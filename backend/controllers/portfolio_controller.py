"""Authenticated declared holdings; allocation publication remains gated."""
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from backend.core.dependencies import get_current_user
from backend.core.database import get_db
from backend.models.models import User
from backend.schemas.portfolio import HoldingsWrite, SuitabilityWrite, CSVPreview, ShockRequest, AllocationScenario
from backend.services import portfolio_service as portfolio, allocation_service as allocation

router = APIRouter(tags=['portfolio'])


@router.post('/portfolio/holdings')
def save_holdings(payload: HoldingsWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.write(db, user.id, 'holdings', payload)


@router.get('/portfolio/holdings')
def holdings(revision: int | None = Query(None, ge=1), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.describe(portfolio.get(db, user.id, 'holdings', revision))


@router.post('/portfolio/csv-preview')
def preview(payload: CSVPreview, user: User = Depends(get_current_user)):
    return portfolio.csv_preview(payload)


@router.get('/portfolio/valuation')
def valuation(as_of: date | None = None, revision: int | None = Query(None, ge=1),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.valuation(db, user.id, as_of, revision)


@router.post('/portfolio/scenarios')
def shock(payload: ShockRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.scenario(db, user.id, payload)


@router.post('/portfolio/suitability')
def save_suitability(payload: SuitabilityWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.write(db, user.id, 'suitability', payload)


@router.get('/portfolio/suitability')
def suitability(revision: int | None = Query(None, ge=1), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return portfolio.describe(portfolio.get(db, user.id, 'suitability', revision))


@router.post('/allocation-scenarios')
def allocate(payload: AllocationScenario, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return allocation.create_owned_scenario(db, user.id, payload)


@router.get('/allocation-plans/{identity}')
def plan(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return allocation.read_owned_plan(db, user.id, identity)


@router.post('/allocation-proposals')
def propose(user: User = Depends(get_current_user)):
    return allocation.propose()


@router.get('/allocation-assumptions')
def assumptions(user: User = Depends(get_current_user)):
    from backend.finance.allocation_assumptions import load_register
    try:
        register = load_register()
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'assumptions not validated; register unavailable') from exc
    return {**register.model_dump(mode='json'), 'public_eligible': False,
            'recommendation_status': 'assumptions not validated'}
