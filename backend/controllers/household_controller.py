from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.schemas.household import (NetWorthWrite, HouseholdCreate, InviteCreate, InviteAccept,
                                      GrantWrite, MembershipRevoke, ProtectionWrite)
from backend.services import household_service as service

router = APIRouter(tags=['Synthetic households'])


@router.post('/policies')
def policies_write(payload: ProtectionWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.write(db, user.id, 'protection', payload)


@router.get('/policies')
def policies_read(response: Response, revision: int | None = Query(None, ge=1),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.enabled()
    response.headers['Cache-Control'] = 'no-store'
    row = service.latest(db, user.id, 'protection', revision)
    if not row:
        raise HTTPException(404, 'Resource not found.')
    return {**service.describe(row), 'notice': 'Declared inventory only; insurance adequacy and legal succession are not evaluated.'}


@router.post('/households')
def create_house(payload: HouseholdCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.create_house(db, user.id, payload)


@router.post('/households/{identity}/invites')
def invite(identity: str, payload: InviteCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.core.throttle import consume_attempt
    service.enabled()
    if not consume_attempt(db, 'household-invite:' + str(user.id)):
        raise HTTPException(429, 'Too many invitations; retry later.')
    return service.invite(db, user.id, identity, payload)


@router.post('/household-invites/{identity}/accept')
def accept(identity: str, payload: InviteAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.core.throttle import consume_attempt
    service.enabled()
    if not consume_attempt(db, 'household-accept:' + str(user.id)):
        raise HTTPException(429, 'Too many invitation attempts; retry later.')
    return service.accept(db, user.id, identity, payload)


@router.put('/households/{identity}/grants')
def grant(identity: str, payload: GrantWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.grant(db, user.id, identity, payload)


@router.post('/households/{identity}/members/{member_id}/revoke')
def revoke(identity: str, member_id: int, payload: MembershipRevoke,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.revoke_member(db, user.id, identity, member_id, payload)


@router.get('/households/{identity}/views/{source}/{view}')
def shared(identity: str, source: int, view: str, response: Response, resource: str | None = None,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    return service.shared_view(db, user.id, identity, source, view, resource=resource)


@router.get('/households/{identity}/snapshot')
def consolidated(identity: str, response: Response,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    return service.consolidated_view(db, user.id, identity)


@router.post('/households/{identity}/exports/{source}/{view}')
def export_request(identity: str, source: int, view: str, resource: str | None = None,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.request_export(db, user.id, identity, source, view, resource=resource)


@router.get('/household-exports/{identity}')
def export_fetch(identity: str, response: Response,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    return service.fetch_export(db, user.id, identity)


@router.post('/networth')
def write(payload: NetWorthWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.write(db, user.id, 'networth', payload)


@router.get('/networth')
def read(response: Response, revision: int | None = Query(None, ge=1),
         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.enabled()
    response.headers['Cache-Control'] = 'no-store'
    row = service.latest(db, user.id, 'networth', revision)
    if not row:
        raise HTTPException(404, 'Resource not found.')
    return {**service.describe(row), 'snapshot': service.consolidate([row.data])}
