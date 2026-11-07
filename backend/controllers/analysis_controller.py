from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.schemas.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    FinancialStateResponse,
    LastAnalysisResponse,
)
from backend.services.analysis_service import AnalysisService
from backend.core.limits import reserve
from backend.core.config import config

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("", response_model=AnalysisResponse)
def run_analysis(
    payload: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run AI financial analysis for the saved profile.

    analysis_type options: full | quick | health | investment | credit |
    optimizer | simulation | rebalance | summary

    Include ``scenario`` to run a one-off what-if on top of the saved profile;
    the saved profile and its revision are never changed by a scenario run.
    ``status`` is complete | degraded | partial | failed | superseded; check it
    rather than assuming success.
    """
    reserve(db, current_user.id, "analysis", 1, config.ANALYSIS_DAILY_LIMIT)
    db.commit()  # bound attempted expensive work, including failed attempts
    scenario = payload.scenario.model_dump(exclude_unset=True) if payload.scenario else None
    output = AnalysisService(db).run(payload.analysis_type, current_user.id, scenario)
    return AnalysisResponse(analysis_type=payload.analysis_type, **output)


@router.get("/last", response_model=LastAnalysisResponse)
def get_last_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Latest saved result per section, with stale flags against the current profile revision."""
    result = AnalysisService(db).get_last(current_user.id)
    return LastAnalysisResponse(found=bool(result), **result) if result else LastAnalysisResponse(found=False)


@router.get("/state", response_model=FinancialStateResponse)
def get_financial_state(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Health score (None when unknown) and declared holdings; projections are never reported here."""
    return FinancialStateResponse(**AnalysisService(db).get_state(current_user.id))
