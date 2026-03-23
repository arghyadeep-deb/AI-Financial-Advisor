from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user, profile_to_dict
from backend.schemas.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    FinancialStateResponse,
    LastAnalysisResponse
)
from backend.services.analysis_service import AnalysisService
from backend.services.profile_service import ProfileService
from backend.models.models import User

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("", response_model=AnalysisResponse)
def run_analysis(
    payload:      AnalysisRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Run AI financial analysis.

    analysis_type options:
    - full       → all 7 agents
    - quick      → health + investment + credit only
    - health     → health score only
    - investment → investment plan + stocks
    - credit     → credit card recommendations
    - optimizer  → optimization opportunities
    - simulation → wealth projections
    - rebalance  → portfolio rebalancing
    - summary    → executive summary
    """

    # Get profile
    profile = ProfileService(db).get(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Complete your financial profile at POST /profile before running analysis."
        )

    # Run analysis
    output = AnalysisService(db).run(
        analysis_type = payload.analysis_type,
        profile_dict  = profile_to_dict(profile),
        user_id       = current_user.id
    )

    return AnalysisResponse(
        success       = output.get("success", True),
        analysis_type = payload.analysis_type,
        results       = output.get("results", {}),
        errors        = output.get("errors",  {})
    )


@router.get("/last", response_model=LastAnalysisResponse)
def get_last_analysis(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Get last saved analysis results without re-running agents."""
    result = AnalysisService(db).get_last(current_user.id)
    return LastAnalysisResponse(
        found   = bool(result),
        results = result
    )


@router.get("/state", response_model=FinancialStateResponse)
def get_financial_state(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Get health score and portfolio value."""
    state = AnalysisService(db).get_state(current_user.id)
    return FinancialStateResponse(**state)