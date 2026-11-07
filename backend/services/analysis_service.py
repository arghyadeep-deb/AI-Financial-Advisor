"""Analysis orchestration (T105 / T106; FR-001..FR-005, FR-007).

* Every run is an ``Analysis`` row: owner, kind, status, profile revision,
  rule version, timestamps and per-section provenance.
* Inputs come from ONE canonical ``FinanceSnapshot``; ``output_guard``
  enforces it on whatever agents/models returned.
* Scenario runs (``scenario`` overrides) never write the saved profile.
* A run that finishes after the saved profile moved to a newer revision is
  stored as ``superseded`` and never becomes current state.
* "Latest" is chosen per section by recency, not by preferring full runs.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from agents.graph_executor import GraphExecutor
from backend.core.money import paise_to_float
from backend.models.models import Analysis, FinancialProfile, FinancialState
from backend.services import output_guard
from backend.services.profile_service import ProfileService, snapshot_for, to_agent_dict
from engines.cashflow import RULE_VERSION
from engines.financial_health_engine import FinancialHealthEngine

log = logging.getLogger("advisor.analysis")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AnalysisService:

    VALID_TYPES = [
        "full", "quick", "health", "investment",
        "credit", "optimizer", "simulation",
        "rebalance", "summary",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.executor = GraphExecutor()

    # ── run ───────────────────────────────────────────────────────────────
    def run(self, analysis_type: str, user_id: int, scenario: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if analysis_type not in self.VALID_TYPES:
            raise HTTPException(status_code=400,
                                detail=f"Invalid analysis_type. Must be one of: {self.VALID_TYPES}")
        profile = ProfileService(self.db).get(user_id)
        if not profile:
            raise HTTPException(status_code=400,
                                detail="Complete your financial profile at POST /profile before running analysis.")

        # an explicit null credit_score means "unknown" for this what-if; other nulls are ignored
        overrides = {k: v for k, v in (scenario or {}).items() if v is not None or k == "credit_score"}
        is_scenario = bool(overrides)
        snapshot = snapshot_for(profile, overrides)          # raises ProfileIncomplete (422) if unknown inputs
        started_revision = profile.revision

        agent_profile = to_agent_dict(profile, overrides)
        agent_profile["available_monthly_contribution"] = (
            paise_to_float(snapshot.available_contribution_paise)
            if snapshot.available_contribution_paise is not None else None)
        agent_profile["monthly_shortfall"] = paise_to_float(snapshot.shortfall_paise)

        record = Analysis(
            id=str(uuid.uuid4()), user_id=user_id, kind=analysis_type, status="running",
            profile_revision=started_revision, rule_version=f"{RULE_VERSION}/{output_guard.GUARD_VERSION}",
            is_scenario=is_scenario, started_at=_now(), snapshot=snapshot.to_dict())
        self.db.add(record)
        self.db.commit()

        log.info("analysis start id=%s kind=%s revision=%s scenario=%s",
                 record.id, analysis_type, started_revision, is_scenario)

        try:
            if analysis_type == "full":
                output = self.executor.execute_full_analysis(agent_profile)
            elif analysis_type == "quick":
                output = self.executor.execute_quick_analysis(agent_profile)
            else:
                output = self.executor.execute_single(analysis_type, agent_profile)
            results = output.get("results", {})
            errors = output.get("errors", {})
            engine_health = FinancialHealthEngine().calculate(agent_profile) if "health" in results else None
            results, section_status, status = output_guard.enforce(
                results, errors, snapshot, agent_profile, engine_health)
        except Exception as exc:                              # never leave a run "running"
            log.exception("analysis failed id=%s", record.id)
            record.status = "failed"
            record.completed_at = _now()
            record.errors = {"analysis": type(exc).__name__}
            self.db.commit()
            raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

        # Stale-completion check: re-read the CURRENT revision.
        self.db.expire_all()
        current = ProfileService(self.db).get(user_id)
        stale = (not is_scenario) and current is not None and current.revision != started_revision
        record.status = "superseded" if stale else status
        record.completed_at = _now()
        record.results = results
        record.errors = {k: str(v)[:200] for k, v in errors.items()}
        record.section_status = section_status
        self.db.commit()

        if not stale and not is_scenario and "health" in results:
            h = results["health"]
            self._update_state(user_id, h.get("overall_score"), snapshot, started_revision)

        return {
            "analysis_id": record.id,
            "success": record.status == "complete",
            "status": record.status,
            "results": results,
            "errors": record.errors,
            "is_scenario": is_scenario,
            "profile_revision": started_revision,
            "stale": stale,
            "section_status": section_status,
            "snapshot": snapshot.to_dict(),
        }

    # ── read ──────────────────────────────────────────────────────────────
    def get_last(self, user_id: int) -> Dict[str, Any]:
        """Latest result per section (by recency) across non-scenario runs."""
        profile = ProfileService(self.db).get(user_id)
        current_rev = profile.revision if profile else None
        rows: List[Analysis] = (
            self.db.query(Analysis)
            .filter(Analysis.user_id == user_id, Analysis.is_scenario.is_(False),
                    Analysis.status.in_(["complete", "degraded", "partial", "superseded"]))
            .order_by(Analysis.completed_at.desc(), Analysis.started_at.desc())
            .all())
        if not rows:
            return {}
        # A late-finishing run for an old revision must not displace results for the current one.
        rows.sort(key=lambda r: current_rev is not None and r.profile_revision != current_rev)
        merged: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}
        sect_status: Dict[str, Any] = {}
        by_kind: Dict[str, Any] = {}
        for r in rows:                                      # newest first
            by_kind.setdefault(r.kind, {
                "analysis_id": r.id, "status": r.status, "profile_revision": r.profile_revision,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None})
            for name, res in (r.results or {}).items():
                if name not in merged:
                    merged[name] = res
                    meta[name] = {"analysis_id": r.id, "profile_revision": r.profile_revision,
                                  "stale": current_rev is not None and r.profile_revision != current_rev,
                                  "completed_at": r.completed_at.isoformat() if r.completed_at else None}
                    sect_status[name] = (r.section_status or {}).get(name, {})
        newest = rows[0]
        return {
            "results": merged,
            "analysis_id": newest.id,
            "status": newest.status,
            "profile_revision": newest.profile_revision,
            "current_revision": current_rev,
            "stale": any(m["stale"] for m in meta.values()),
            "completed_at": newest.completed_at,
            "section_status": {**sect_status, "_meta": meta},
            "by_kind": by_kind,
            "snapshot": newest.snapshot or {},
        }

    def get_state(self, user_id: int) -> Dict[str, Any]:
        profile = ProfileService(self.db).get(user_id)
        state = self.db.query(FinancialState).filter(FinancialState.user_id == user_id).first()
        current_rev = profile.revision if profile else None
        declared = paise_to_float(profile.existing_investments_paise) if profile else None
        if not state or state.health_score_known is None:
            return {
                "health_score": None, "portfolio_value": declared, "monthly_savings_rate": None,
                "last_updated": None, "profile_revision": current_rev, "health_score_revision": None,
                "stale": False,
                "message": "No analysis run yet. Run POST /analysis first.",
            }
        known = bool(state.health_score_known)
        return {
            "health_score": state.health_score if known else None,
            "portfolio_value": declared,
            "monthly_savings_rate": state.monthly_savings_rate,
            "last_updated": state.last_updated,
            "profile_revision": current_rev,
            "health_score_revision": state.health_score_revision,
            "stale": state.health_score_revision is not None and state.health_score_revision != current_rev,
            "message": None,
        }

    # ── internals ─────────────────────────────────────────────────────────
    def _update_state(self, user_id: int, score: Optional[float], snapshot, revision: int) -> None:
        """Persist the latest health score.  ``portfolio_value`` is NOT written:
        observed holdings are read from the profile, projections never land here."""
        if self.db.query(FinancialState).filter(FinancialState.user_id == user_id).first() is None:
            self.db.add(FinancialState(user_id=user_id, portfolio_value=0))
            self.db.commit()
        known = isinstance(score, (int, float))
        rate = (snapshot.surplus_paise / snapshot.income_paise * 100) if snapshot.income_paise else 0.0
        current_rev = (select(FinancialProfile.revision)
                       .where(FinancialProfile.user_id == user_id).scalar_subquery())
        # ONE statement: only write if the profile is still at this run's revision and no newer run
        # already wrote state.  Validation and write cannot be separated by another request.
        self.db.execute(
            update(FinancialState)
            .where(FinancialState.user_id == user_id,
                   current_rev == revision,
                   or_(FinancialState.health_score_revision.is_(None),
                       FinancialState.health_score_revision <= revision))
            .values(health_score=round(float(score), 1) if known else None,
                    health_score_known=known, health_score_revision=revision,
                    monthly_savings_rate=round(rate, 2),     # signed: a deficit stays negative
                    last_updated=_now()))
        self.db.commit()
