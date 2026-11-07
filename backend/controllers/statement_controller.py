from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.core.config import config
from backend.models.models import User, StatementAccount, StatementDocument, StatementImport, StatementRow, LedgerEntry, LedgerCorrection
from backend.schemas.statements import AccountCreate, Operation, Review, Split, LinkCreate, ReportCreate
from backend.services import statement_service as service, monthly_report_service as reports
from backend.finance import ledger
from backend.finance.importers.registry import limits

router = APIRouter(tags=['Synthetic statements'])


@router.get('/statement-formats')
def formats(user: User = Depends(get_current_user)):
    return limits()


@router.post('/statement-accounts', status_code=201)
def account(payload: AccountCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = service.create_account(db, user.id, payload)
    return {'id': row.id, **payload.model_dump(), 'revision': row.revision}


@router.get('/statement-accounts')
def accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{'id': a.id, 'label': a.label, 'token': a.token, 'account_type': a.account_type,
             'revision': a.revision, 'link_revision': a.link_revision}
            for a in db.query(StatementAccount).filter_by(user_id=user.id).order_by(StatementAccount.id).limit(100)]


@router.get('/statement-accounts/vector')
def scope_vector(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.vector(db, user.id)


@router.post('/statement-accounts/{account_id}/uploads', status_code=202)
async def upload(account_id: str, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.owned(db, StatementAccount, user.id, account_id)
    service.enabled()
    if request.headers.get('content-type', '').split(';')[0] not in {'text/csv', 'text/plain'}:
        raise HTTPException(415, 'Only the documented synthetic CSV/text format is supported.')
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > config.STATEMENT_MAX_BYTES:
            raise HTTPException(413, 'Statement exceeds the configured byte limit.')
        data.extend(chunk)
    return service.describe(service.upload(db, user.id, account_id, bytes(data)))


@router.get('/statement-imports')
def imports(user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0)):
    return [service.describe(j) for j in db.query(StatementImport).filter_by(user_id=user.id).order_by(StatementImport.created_at.desc(), StatementImport.id).offset(offset).limit(100)]


@router.get('/statement-imports/{import_id}')
def status(import_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.describe(service.owned(db, StatementImport, user.id, import_id))


@router.get('/statement-imports/{import_id}/rows')
def rows(import_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0)):
    job = service.owned(db, StatementImport, user.id, import_id)
    matches = ledger.candidates(db, user.id, job)
    return [{'id': r.id, 'source_row': r.ordinal, 'posting_date': r.posting_date, 'amount_paise': r.amount_paise,
             'description': r.description, 'reference': r.reference, 'category': r.category,
             'classification_source': 'synthetic_user_assertion', 'candidate_entry_ids': matches.get(r.id, [])}
            for r in ledger.source_rows(db, user.id, job.id)[offset:offset+100]]


@router.get('/statement-documents/{document_id}/content')
def document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response(service.read_document(db, user.id, document_id), media_type='text/plain',
        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename="synthetic-statement.txt"',
                 'X-Content-Type-Options': 'nosniff'})


@router.post('/statement-imports/{import_id}/resume')
def resume(import_id: str, payload: Review, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.publish(db, user.id, import_id, payload)


@router.post('/statement-imports/{import_id}/reverse')
def reverse(import_id: str, payload: Operation, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.reverse(db, user.id, import_id, payload)


@router.post('/statement-imports/{import_id}/cancel')
def cancel(import_id: str, payload: Operation, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.cancel(db, user.id, import_id, payload)


@router.post('/statement-imports/{import_id}/reprocess')
def reprocess(import_id: str, payload: Operation, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.reprocess(db, user.id, import_id, payload)


@router.get('/statement-imports/{import_id}/events')
def events(import_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0)):
    service.owned(db, StatementImport, user.id, import_id)
    return [{'id': r.id, 'operation': r.payload['operation'], 'created_at': r.created_at, 'result': r.after}
            for r in db.query(LedgerCorrection).filter_by(user_id=user.id, target_id=import_id).order_by(LedgerCorrection.created_at, LedgerCorrection.id).offset(offset).limit(100)]


@router.get('/statement-imports/{import_id}/comparison')
def generation_comparison(import_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.generation_comparison(db, user.id, import_id)


@router.get('/ledger')
def entries(user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0)):
    return [{key: getattr(e, key) for key in ('id', 'account_id', 'posting_date', 'amount_paise', 'components', 'revision', 'active')}
            for e in db.query(LedgerEntry).filter_by(user_id=user.id).order_by(LedgerEntry.id).offset(offset).limit(100)]


@router.post('/ledger/{entry_id}/splits')
def split(entry_id: str, payload: Split, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.split(db, user.id, entry_id, payload)


@router.post('/ledger-links', status_code=201)
def link(payload: LinkCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.confirm_link(db, user.id, payload)


@router.post('/ledger-links/{link_id}/reverse')
def reverse_link(link_id: str, payload: Operation, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ledger.reverse_link(db, user.id, link_id, payload)


@router.post('/monthly-reports', status_code=201)
def report(payload: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.create(db, user.id, payload)


@router.get('/monthly-reports')
def report_history(month: str | None = Query(default=None, pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),
                   offset: int = Query(0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.models.models import MonthlyReport
    query = db.query(MonthlyReport).filter_by(user_id=user.id)
    if month:
        query = query.filter_by(month=month)
    return [reports.read(db, user.id, r.id) for r in query.order_by(
        MonthlyReport.month.desc(), MonthlyReport.created_at.desc(), MonthlyReport.id.desc()).offset(offset).limit(100)]


@router.get('/monthly-reports/{report_id}/transactions')
def report_evidence(report_id: str, offset: int = Query(0, ge=0), category: str | None = None,
                    budget_category: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = reports.read(db, user.id, report_id)
    rows = report['snapshot']['sources']
    if category:
        rows = [r for r in rows if any(c['category'] == category for c in r['components'])]
    if budget_category:
        rows = [r for r in rows if any(c.get('budget_category') == budget_category for c in r['components'])]
    return {'report_id': report_id, 'stale': report['stale'], 'sources': rows[offset:offset+100],
            'restatement': report['snapshot'].get('restatement')}


@router.get('/monthly-reports/{report_id}')
def read_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.read(db, user.id, report_id)


@router.get('/monthly-reports/{report_id}/export.csv')
def export(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response(reports.export_csv(db, user.id, report_id), media_type='text/csv',
        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename="monthly-report.csv"'})
