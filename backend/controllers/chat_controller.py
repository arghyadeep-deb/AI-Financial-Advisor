import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import Message, Thread, User
from backend.schemas.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService
from backend.core.limits import reserve
from backend.core.config import config


def _reserve_chat(db, owner, payload):
    # Completed idempotent retries are reads and do not consume another unit.
    prior = db.query(Message).filter_by(user_id=owner, client_message_id=payload.client_message_id,
                                       role="user").first() if payload.client_message_id else None
    if prior and db.query(Message).filter_by(thread_id=prior.thread_id,
            client_message_id=payload.client_message_id, role="assistant").first():
        return
    reserve(db, owner, "chat", 1, config.CHAT_DAILY_LIMIT)
    db.commit()

router = APIRouter(prefix="/chat", tags=["Chat"])
log = logging.getLogger("advisor.chat")


# ─── Standard Chat ────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Standard chat endpoint — returns the full reply at once.

    Send a unique ``client_message_id`` per user message. Retrying a request with
    the same id never creates a second turn: the stored reply is returned
    (``replayed: true``). ``status`` is ``degraded`` when the models were
    unavailable and a deterministic reply built from your verified numbers was
    returned instead.
    """
    _reserve_chat(db, current_user.id, payload)
    service = ChatService(db)
    thread_id = service.get_or_create_thread(
        user_id=current_user.id, thread_id=payload.thread_id, message=payload.message,
        user_name=current_user.full_name, user_email=current_user.email,
        client_message_id=payload.client_message_id)
    result = service.chat(
        user_id=current_user.id, user_name=current_user.full_name, message=payload.message,
        thread_id=thread_id, client_message_id=payload.client_message_id)
    return ChatResponse(**result)


# ─── Streaming Chat ───────────────────────────────────────────────────────────

@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Streaming chat — Server-Sent Events.

        data: {"chunk": "Hello", "thread_id": 1}
        data: {"done": true, "thread_id": 1, "full_reply": "...", "status": "ok|degraded", "replayed": false}
        data: {"error": "...", "retryable": true}      (stream broke; retry with the same client_message_id)

    The same ``client_message_id`` rule as POST /chat applies.
    """
    _reserve_chat(db, current_user.id, payload)
    service = ChatService(db)
    thread_id = service.get_or_create_thread(
        user_id=current_user.id, thread_id=payload.thread_id, message=payload.message,
        user_name=current_user.full_name, user_email=current_user.email,
        client_message_id=payload.client_message_id)

    def generate():
        try:
            for event in service.chat_stream(
                user_id=current_user.id, user_name=current_user.full_name, message=payload.message,
                thread_id=thread_id, client_message_id=payload.client_message_id,
            ):
                yield f"data: {json.dumps({'thread_id': thread_id, **event})}\n\n"
        except HTTPException as exc:
            yield f"data: {json.dumps({'error': exc.detail if isinstance(exc.detail, str) else exc.detail.get('message', 'Request failed.'), 'retryable': False})}\n\n"
        except Exception as exc:
            log.error("chat stream failed: %s", type(exc).__name__)
            yield f"data: {json.dumps({'error': 'Something went wrong. Please retry.', 'retryable': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ─── Chat History ─────────────────────────────────────────────────────────────

@router.get("/history/{thread_id}")
def get_chat_history(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full chat history for one of your threads (missing and foreign threads look identical)."""
    thread = db.query(Thread).filter(Thread.id == thread_id, Thread.user_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")

    messages = (
        db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at, Message.id).all()
    )
    return {
        "thread_id": thread_id,
        "title": thread.title,
        "user_name": thread.user_name,
        "user_email": thread.user_email,
        "created_at": thread.created_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "user_name": m.user_name or (current_user.full_name if m.role == "user" else "AI Advisor"),
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }
