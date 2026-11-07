"""Chat (T110 / FR-007).

* One logical turn per ``client_message_id``: a retry returns the stored turn
  (or resumes a turn whose reply never arrived) instead of adding a second
  user message.  Enforced by a DB unique constraint, so it holds under races.
* Context comes from the canonical ``FinanceSnapshot`` and the latest stored
  analysis sections; the model cannot change those values.
* Provider outage => deterministic reply built from the snapshot, flagged
  ``degraded``.  A model reply that contradicts the facts (surplus claimed
  during a deficit, a SIP amount recommended when none is affordable) is
  replaced by the same deterministic reply.
"""
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.money import format_inr
from backend.core.telemetry import traceable
from backend.models.models import Message, Thread
from backend.services import output_guard
from backend.services.analysis_service import AnalysisService
from engines.cashflow import FinanceSnapshot
from memory.conversation_memory import ConversationMemory
from utils.llm_brain import ProviderUnavailable, StreamInterrupted, call_llm, stream_llm

log = logging.getLogger("advisor.chat")


IN_FLIGHT_SECONDS = 30.0     # a user turn younger than this with no reply is presumed still being answered


@dataclass
class Turn:
    replay: Optional[str] = None            # stored assistant reply for this client_message_id
    replay_status: str = "ok"
    user_message_recorded: bool = False
    thread_id: Optional[int] = None         # set when the turn resolved to an earlier thread


def deterministic_reply(user_name: str, snap: Optional[FinanceSnapshot]) -> str:
    if snap is not None and snap.coverage.startswith('observed_ledger'):
        return (f'Observed account activity for {snap.as_of}: income {format_inr(snap.income_paise)}, '
                f'net spending {format_inr(snap.expenses_paise)}, '
                f'shortfall {format_inr(snap.shortfall_paise)}. {snap.contribution_reason} '
                'Review coverage, source revisions and confirmed upcoming obligations before making a plan.')
    if snap is None:
        return (f"I can't reach my analysis models right now, {user_name}, and your profile isn't complete yet. "
                "Please complete your profile and try again shortly.")
    if snap.shortfall_paise > 0:
        facts = (f"Your monthly expenses exceed your income by {format_inr(snap.shortfall_paise)}, so there is "
                 "nothing to invest right now.")
        step = "Next step: list your three biggest expenses today and pick one to reduce this week."
    elif snap.available_contribution_paise:
        facts = (f"Based on your profile, roughly {format_inr(snap.available_contribution_paise)} a month looks "
                 "available to invest after obligations and your emergency-fund top-up.")
        step = "Next step: check that figure against your real bank statement before you commit to anything."
    elif snap.contribution_status == "unavailable":
        facts = snap.contribution_reason
        step = "Next step: add your monthly debt payment to your profile."
    else:
        facts = "After your obligations and emergency-fund top-up there is nothing left to invest this month."
        step = "Next step: review your fixed costs to see where room could be made."
    return (f"I'm temporarily unable to reach the AI models, {user_name}, so here are the recorded numbers "
            f"from your profile. {facts} {step}")


class ChatService:

    def __init__(self, db: Session):
        self.db = db
        self.conv_memory = ConversationMemory(db)

    # ─── Threads ──────────────────────────────────────────────────────────
    def get_or_create_thread(self, user_id: int, thread_id: Optional[int], message: str,
                             user_name: str = None, user_email: str = None,
                             client_message_id: Optional[str] = None) -> int:
        if thread_id:
            thread = self.conv_memory.get_thread(thread_id)
            if thread and thread.user_id == user_id:
                return thread_id
            # Someone else's or missing thread: same answer, no information leak.
            raise HTTPException(status_code=404, detail="Thread not found.")
        if client_message_id:
            # A retried first message (thread id never reached the client) reuses its thread.
            prior = (self.db.query(Message)
                     .filter(Message.user_id == user_id, Message.role == "user",
                             Message.client_message_id == client_message_id)
                     .order_by(Message.id).first())
            if prior is not None:
                return prior.thread_id
        thread = self.conv_memory.create_thread(
            user_id=user_id, title=message[:50], thread_type="chat",
            user_name=user_name, user_email=user_email)
        return thread.id

    # ─── Idempotent turns ─────────────────────────────────────────────────
    def _find(self, thread_id: int, cid: str, role: str) -> Optional[Message]:
        return (self.db.query(Message)
                .filter(Message.thread_id == thread_id, Message.client_message_id == cid, Message.role == role)
                .first())

    def begin_turn(self, user_id: int, user_name: str, thread_id: int, message: str,
                   client_message_id: Optional[str]) -> Turn:
        if client_message_id:
            prior = self._find(thread_id, client_message_id, "user")
            if prior is not None:
                if prior.content != message:
                    raise HTTPException(409, detail={"code": "idempotency_conflict",
                                                     "message": "That message id was already used with different text."})
                done = self._find(thread_id, client_message_id, "assistant")
                if done is not None:
                    return Turn(replay=done.content, replay_status=(done.extra_data or {}).get("status", "ok"),
                                user_message_recorded=True)
                done = self._await_inflight_reply(prior, thread_id, client_message_id)
                if done is not None:
                    return Turn(replay=done.content, replay_status=(done.extra_data or {}).get("status", "ok"),
                                user_message_recorded=True)
                return Turn(user_message_recorded=True)
        msg = Message(thread_id=thread_id, user_id=user_id, user_name=user_name, role="user",
                      content=message, extra_data={}, client_message_id=client_message_id)
        self.db.add(msg)
        try:
            self.db.commit()
        except IntegrityError:               # concurrent duplicate of the same logical turn
            self.db.rollback()
            prior = (self.db.query(Message)
                     .filter(Message.user_id == user_id, Message.role == "user",
                             Message.client_message_id == client_message_id).first()
                     if client_message_id else None)
            if prior is None:
                raise
            if prior.thread_id != thread_id:  # lost the race for a first message: drop our empty thread
                self._drop_empty_thread(thread_id)
            turn = self.begin_turn(user_id, user_name, prior.thread_id, message, client_message_id)
            turn.thread_id = prior.thread_id
            return turn
        return Turn(user_message_recorded=True, thread_id=thread_id)

    def _await_inflight_reply(self, prior: Message, thread_id: int, cid: str) -> Optional[Message]:
        """A duplicate of a turn that is still being answered waits for that reply instead of calling
        the model a second time.  An old unanswered turn (crash / interrupted stream) is retried."""
        created = prior.created_at or datetime.now(timezone.utc).replace(tzinfo=None)
        age = (datetime.now(timezone.utc).replace(tzinfo=None) - created).total_seconds()
        deadline = time.monotonic() + max(0.0, IN_FLIGHT_SECONDS - age)
        while time.monotonic() < deadline:
            time.sleep(0.25)
            self.db.expire_all()
            done = self._find(thread_id, cid, "assistant")
            if done is not None:
                return done
        return None

    def _drop_empty_thread(self, thread_id: int) -> None:
        if self.db.query(Message).filter(Message.thread_id == thread_id).count() == 0:
            self.db.query(Thread).filter(Thread.id == thread_id).delete()
            self.db.commit()

    def finish_turn(self, thread_id: int, reply: str, status: str, client_message_id: Optional[str]) -> str:
        msg = Message(thread_id=thread_id, user_id=None, user_name="AI Advisor", role="assistant",
                      content=reply, extra_data={"status": status}, client_message_id=client_message_id)
        self.db.add(msg)
        try:
            self.db.commit()
            return reply
        except IntegrityError:               # another request already stored this turn's reply
            self.db.rollback()
            existing = self._find(thread_id, client_message_id, "assistant") if client_message_id else None
            return existing.content if existing else reply

    # ─── Context ──────────────────────────────────────────────────────────
    def _snapshot(self, user_id: int) -> Optional[FinanceSnapshot]:
        from backend.services.finance_snapshot_service import current_snapshot
        return current_snapshot(self.db, user_id)

    def _build_prompts(self, user_id: int, user_name: str, message: str, thread_id: int,
                       snap: Optional[FinanceSnapshot]) -> tuple:
        last = AnalysisService(self.db).get_last(user_id)
        results = last.get("results", {}) if last else {}
        stale = bool(last and last.get("stale"))
        health = results.get("health", {}) or {}
        inv = results.get("investment", {}) or {}
        credit = results.get("credit", {}) or {}
        if snap and snap.coverage.startswith('observed_ledger'):
            # Profile-era recommendations cannot override the ledger's unavailable cap.
            inv = {}

        if snap is None:
            facts = "The user's profile is missing or incomplete. Ask them to complete it before giving numbers."
        else:
            facts = "\n".join([
                f"Source coverage and period: {snap.coverage}; {snap.as_of}; {snap.contribution_reason}",
                f"Monthly income            : {format_inr(snap.income_paise)}",
                f"Monthly expenses          : {format_inr(snap.expenses_paise)}",
                (f"MONTHLY SHORTFALL         : {format_inr(snap.shortfall_paise)} (expenses exceed income)"
                 if snap.shortfall_paise > 0 else f"Monthly surplus           : {format_inr(snap.surplus_paise)}"),
                f"Emergency fund gap        : {format_inr(snap.emergency_gap_paise)}",
                f"Available to invest/month : "
                f"{format_inr(snap.available_contribution_paise) if snap.available_contribution_paise is not None else 'UNAVAILABLE'}"
                f" ({snap.contribution_status}; {snap.contribution_reason})",
                f"Credit score              : {snap.credit_score if snap.credit_score is not None else 'UNKNOWN - never guess'}",
            ])
        plan = [f"  - {s.get('instrument', '')}: Rs {s.get('monthly_amount', 0):,.0f}/month"
                for s in (inv.get("monthly_sip_plan") or [])]
        analysis_txt = (
            f"Health score: {health.get('overall_score', 'not run yet')}/100 (grade {health.get('grade', 'N/A')})\n"
            f"Planned monthly investments (generic instruments):\n{chr(10).join(plan) if plan else '  none'}\n"
            f"Top credit card: {(credit.get('recommendations') or [{}])[0].get('card_name', '') if credit else ''}\n"
            + ("NOTE: these analysis results are OUTDATED because the profile changed since they were produced.\n"
               if stale else ""))

        kb_context = ""
        try:
            from rag.rag_router import route_query
            kb_context = route_query(message, mode="auto")
        except Exception:
            log.info("knowledge-base lookup unavailable")

        history = self.conv_memory.get_history(thread_id)
        history_text = "".join(
            f"{user_name if m['role'] == 'user' else 'AI Advisor'}: {m['content']}\n\n" for m in history[-8:])

        system_prompt = f"""You are a warm, careful AI financial assistant for Indian users, speaking with {user_name}.
Use ONLY the verified facts below for any number about this user. Never invent or alter them.
If AVAILABLE TO INVEST is UNAVAILABLE or zero, do not recommend any SIP or investment amount.
If there is a shortfall, never describe a surplus. If the credit score is UNKNOWN, say it is unknown.
Do not name specific stocks or funds. Keep replies to 3-6 sentences and end with one concrete next step.

=== VERIFIED FACTS (computed by the app) ===
{facts}

=== LATEST ANALYSIS ===
{analysis_txt}"""
        user_message = (f"Previous conversation:\n{history_text or 'This is the start of our conversation.'}\n\n"
                        f"{user_name} asks: {message}\n\n"
                        + (f"Relevant knowledge base context:\n{kb_context}" if kb_context else ""))
        return system_prompt, user_message

    def _validate(self, reply: str, snap: Optional[FinanceSnapshot]) -> Optional[str]:
        product_violation = output_guard.named_product_violation(reply)
        if product_violation:
            return product_violation
        if snap is None or not reply:
            return None
        return output_guard.narrative_violation(reply, set(), snap, check_amounts=False)

    # ─── Standard chat ────────────────────────────────────────────────────
    @traceable(run_type="chain", name="chat_agent", tags=["agent", "chat"])
    def chat(self, user_id: int, user_name: str, message: str, thread_id: int,
             client_message_id: Optional[str] = None) -> Dict[str, Any]:
        turn = self.begin_turn(user_id, user_name, thread_id, message, client_message_id)
        thread_id = turn.thread_id or thread_id
        if turn.replay is not None:
            return {"reply": turn.replay, "thread_id": thread_id, "status": turn.replay_status, "replayed": True}

        snap = self._snapshot(user_id)
        if snap and snap.coverage.startswith('observed_ledger'):
            stored = self.finish_turn(thread_id, deterministic_reply(user_name, snap), 'degraded', client_message_id)
            return {'reply': stored, 'thread_id': thread_id, 'status': 'degraded', 'replayed': False}
        status = "ok"
        try:
            system_prompt, user_message = self._build_prompts(user_id, user_name, message, thread_id, snap)
            reply = call_llm(system_prompt=system_prompt, user_message=user_message,
                             max_tokens=600, agent_name="chat_agent")
            if self._validate(reply, snap):
                reply, status = deterministic_reply(user_name, snap), "degraded"
        except Exception as exc:                      # provider outage, timeout, bad key...
            log.warning("chat model unavailable: %s", type(exc).__name__)
            reply, status = deterministic_reply(user_name, snap), "degraded"

        stored = self.finish_turn(thread_id, reply, status, client_message_id)
        return {"reply": stored, "thread_id": thread_id, "status": status, "replayed": False}

    # ─── Streaming chat ───────────────────────────────────────────────────
    def chat_stream(self, user_id: int, user_name: str, message: str, thread_id: int,
                    client_message_id: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Yields event dicts: {'chunk': str} ... then {'done': True, ...} or {'error': ...}."""
        turn = self.begin_turn(user_id, user_name, thread_id, message, client_message_id)
        thread_id = turn.thread_id or thread_id
        if turn.replay is not None:
            yield {"done": True, "full_reply": turn.replay, "status": turn.replay_status, "replayed": True,
                   "thread_id": thread_id}
            return

        snap = self._snapshot(user_id)
        if snap and snap.coverage.startswith('observed_ledger'):
            stored = self.finish_turn(thread_id, deterministic_reply(user_name, snap), 'degraded', client_message_id)
            yield {'chunk': stored, 'thread_id': thread_id}
            yield {'done': True, 'full_reply': stored, 'status': 'degraded', 'replayed': False, 'thread_id': thread_id}
            return
        system_prompt, user_message = self._build_prompts(user_id, user_name, message, thread_id, snap)
        buffer = ""
        try:
            for chunk in stream_llm(system_prompt=system_prompt, user_message=user_message,
                                    max_tokens=600, agent_name="chat_agent"):
                buffer += chunk
                yield {"chunk": chunk, "thread_id": thread_id}
        except ProviderUnavailable:
            reply = deterministic_reply(user_name, snap)
            stored = self.finish_turn(thread_id, reply, "degraded", client_message_id)
            yield {"chunk": stored, "thread_id": thread_id}
            yield {"done": True, "full_reply": stored, "status": "degraded", "replayed": False, "thread_id": thread_id}
            return
        except StreamInterrupted:
            # Partial text was shown. Nothing is stored for the assistant, the user
            # message stays recorded, and retrying with the same id completes the turn.
            yield {"error": "The reply was interrupted. Please retry.", "retryable": True, "thread_id": thread_id}
            return

        status = "ok"
        if self._validate(buffer, snap):
            # Streamed text already reached the client; store the safe version and tell it to replace.
            buffer, status = deterministic_reply(user_name, snap), "degraded"
        stored = self.finish_turn(thread_id, buffer, status, client_message_id)
        yield {"done": True, "full_reply": stored, "status": status, "replayed": False, "thread_id": thread_id,
               "replace": status == "degraded"}
