"""Internal synthetic scenarios only. No router, LLM, trade or external adapter.

Authenticated adapters must supply the current owner, never take it from model
arguments. Public proposal publication stays gated even with a feasible scenario.
"""
from datetime import date
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.feature_flags import allocation_public_eligible
from backend.finance.suitability import Suitability
from backend.knowledge.registry import Registry
from backend.models.models import AllocationPlan, FinancialProfile
from backend.services.output_guard import guard_allocation
from backend.services.profile_service import snapshot_for
from engines.allocation import allocate, evidence_current
from engines.allocation.contracts import AssumptionPack, Constraints, Holding
from engines.allocation.costs import compare, stress


def _profile(db: Session, owner_id: int) -> FinancialProfile:
    profile = db.query(FinancialProfile).filter_by(user_id=owner_id).first()
    if profile is None:
        raise HTTPException(404, "Allocation input not found")
    return profile


def create_scenario(db: Session, *, owner_id: int, expected_revision: int, suitability: Suitability,
                    pack: AssumptionPack, constraints: Constraints, registry: Registry, as_of: date,
                    holdings: tuple[Holding, ...] | None = None, holdings_revision: str | None = None,
                    model_output=None) -> dict:
    profile = _profile(db, owner_id)
    if profile.revision != expected_revision:
        raise HTTPException(409, "Profile changed; recompute scenario")
    if holdings is not None and not holdings_revision:
        raise HTTPException(422, "Holdings revision required")
    snapshot = snapshot_for(profile)
    result = allocate(snapshot, suitability, pack, constraints, registry, owner_id=owner_id, as_of=as_of)
    payload = guard_allocation({"allocation": result.model_dump(mode="json"),
                               "comparison": compare(result, holdings, pack),
                               "stress": stress(result, pack)}, model_output)
    # Recheck persisted revision before publication; do not trust the identity map.
    current = db.query(FinancialProfile.revision).filter_by(user_id=owner_id).scalar()
    if current != expected_revision:
        raise HTTPException(409, "Profile changed; recompute scenario")
    record = AllocationPlan(id=str(uuid4()), user_id=owner_id, profile_revision=expected_revision,
                            suitability_revision=suitability.revision,
                            input_snapshot={"finance": snapshot.to_dict(),
                                            "suitability": suitability.model_dump(mode="json"),
                                            "assumptions": pack.model_dump(mode="json"),
                                            "constraints": constraints.model_dump(mode="json"),
                                            "holdings_revision": holdings_revision,
                                            "holdings": None if holdings is None else [h.model_dump() for h in holdings],
                                            "as_of": as_of.isoformat()}, result=payload)
    db.add(record)
    db.commit()
    return {"id": record.id, **payload}


def read_plan(db: Session, *, owner_id: int, plan_id: str, registry: Registry, as_of: date,
              suitability_revision: int, holdings_revision: str | None = None,
              assumption_version: str | None = None) -> dict:
    record = db.query(AllocationPlan).filter_by(id=plan_id, user_id=owner_id).first()
    if record is None:
        raise HTTPException(404, "Allocation plan not found")
    profile = _profile(db, owner_id)
    pack = AssumptionPack.model_validate_json(json.dumps(record.input_snapshot["assumptions"]))
    stale = (profile.revision != record.profile_revision
             or suitability_revision != record.suitability_revision
             or holdings_revision != record.input_snapshot["holdings_revision"]
             or assumption_version != pack.version
             or not evidence_current(pack, registry, owner_id, as_of))
    return {"id": record.id, "stale": stale, "inputs": record.input_snapshot,
            **guard_allocation(record.result)}


def propose(*args, **kwargs) -> dict:
    if not allocation_public_eligible():
        return {"status": "gated", "reasons": ["D05 and independent release evidence unresolved"]}
    raise RuntimeError("public allocation has no approved implementation")
