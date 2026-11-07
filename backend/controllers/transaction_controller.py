"""Manual/split facade over the one ledger owner."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.schemas.statements import ManualCash, ManualMatch, Split
from backend.finance import ledger

router = APIRouter(tags=['Synthetic manual cash'])


@router.post('/transactions/manual', status_code=201)
def create(payload: ManualCash, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.manual_cash(db, user.id, payload)


@router.post('/transactions/{identity}/split')
def split(identity: str, payload: Split, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.split(db, user.id, identity, payload)


@router.post('/transactions/{identity}/match-manual')
def match(identity: str, payload: ManualMatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.match_manual(db, user.id, identity, payload)
