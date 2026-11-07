"""Authenticated synthetic tax review. No filing action exists."""
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from backend.core.dependencies import get_current_user
from backend.core.database import get_db
from backend.models.models import User
from backend.schemas.tax import CaseWrite, ReviewWrite, DraftWrite
from backend.services import tax_service as tax

router = APIRouter(prefix='/tax', tags=['tax-sample'])


@router.post('/cases')
def create(payload: CaseWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.write_case(db, user.id, payload)


@router.post('/cases/{case_id}/revisions')
def revise(case_id: str, payload: CaseWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.write_case(db, user.id, payload, case_id)


@router.get('/cases/{case_id}')
def read(case_id: str, revision: int | None = Query(None, ge=1),
         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.case_at(db, user.id, case_id, revision)


@router.post('/cases/{case_id}/reviews')
def review(case_id: str, payload: ReviewWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.review(db, user.id, case_id, payload)


@router.get('/reviews/{identity}')
def evidence(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.describe(tax.owned(db, user.id, identity, 'review'))


@router.post('/cases/{case_id}/drafts')
def draft(case_id: str, payload: DraftWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.draft(db, user.id, case_id, payload)


@router.get('/drafts/{identity}')
def read_draft(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tax.read_draft(db, user.id, identity)


@router.get('/drafts/{identity}/export')
def export(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = tax.export(db, user.id, identity)
    return Response(content, media_type='application/json', headers={
        'Content-Disposition': 'attachment; filename="sample-tax-DRAFT.json"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
