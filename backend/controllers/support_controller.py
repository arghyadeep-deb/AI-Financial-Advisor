"""Owner-facing support controls: grant or revoke support access to one document, and see who looked."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.services import support

router = APIRouter(tags=['Support'])


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str = Field(min_length=1, max_length=36)
    hours: StrictInt = Field(ge=1, le=support.MAX_GRANT_HOURS)


def _grant(g):
    return {'id': g.id, 'document_id': g.document_id, 'expires_at': g.expires_at, 'revoked': g.revoked_at is not None,
            'used': g.used_at is not None}


@router.post('/support/grants', status_code=201)
def create(payload: GrantCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _grant(support.create_grant(db, user.id, payload.document_id, payload.hours))


@router.post('/support/grants/{grant_id}/revoke')
def revoke(grant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _grant(support.revoke_grant(db, user.id, grant_id))


@router.get('/support/access-log')
def log(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return support.access_log(db, user.id)
