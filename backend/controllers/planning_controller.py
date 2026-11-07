"""Authenticated offline planning and Dashboard snapshot contracts."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.schemas import planning as contracts
from backend.services import planning_service as service, planning_calculations as calculations

router = APIRouter(tags=['Offline planning'])


@router.get('/ledger-category-suggestions')
def category_suggestions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.category_suggestions(db, user.id)


@router.get('/finance-snapshot')
def snapshot(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.services.finance_snapshot_service import current_snapshot
    value = current_snapshot(db, user.id)
    return {'found': value is not None, 'snapshot': value.to_dict() if value else None}


@router.get('/planning/vector')
def vector(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.vector(db, user.id)


@router.get('/obligation-candidates')
def candidates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.candidates(db, user.id)


@router.get('/receivables/status')
def receivables(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.receivables(db, user.id)


@router.get('/obligations/{identity}/status')
def obligation_status(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = service.get(db, user.id, 'obligation', identity)
    settlements = [r for r in service.current(db, user.id, 'settlement') if r.data['obligation_id'] == identity]
    valid = [r for r in settlements if service.settlement_valid(db, user.id, r)]
    paid = sum(-service.owned(db, service.LedgerEntry, user.id, r.data['entry_id']).amount_paise for r in valid)
    return {**service.describe(row), 'paid_paise': paid, 'remaining_paise': max(0, row.data['amount_paise']-paid),
        'state': 'archived' if row.data['archived'] else 'paused' if row.data['paused'] else
                 'paid' if paid >= row.data['amount_paise'] else 'partial' if paid else 'unpaid',
        'needs_review_settlement_ids': [r.resource_id for r in settlements if not r.data['reversed'] and r not in valid]}


@router.post('/planning/capacity')
def capacity(payload: contracts.Capacity, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return calculations.capacity(db, user.id, payload)


@router.post('/goal-plans')
def goal_plan(payload: contracts.GoalPlan, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return calculations.goal_plan(db, user.id, payload)


@router.post('/debt-scenarios', status_code=201)
def debt_scenario(payload: contracts.DebtScenario, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return calculations.scenario(db, user.id, payload)


@router.get('/debt-scenarios/{identity}')
def scenario(identity: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.services.monthly_report_service import read
    row = service.get(db, user.id, 'debt_scenario', identity)
    cap = row.data['capacity']
    return {**service.describe(row), 'stale': cap['planning_vector'] != service.vector(db, user.id) or
            read(db, user.id, cap['report_id'])['stale']}


@router.get('/budgets/{identity}/copy-preview')
def copy(identity: str, month: str = Query(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$'), report_id: str | None = None,
         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.copy_budget(db, user.id, identity, month, report_id)


def register_resource(path, kind, contract):
    # Each endpoint retains its concrete Pydantic request schema in OpenAPI.
    def create(payload: contract, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return service.write(db, user.id, kind, payload)

    def edit(identity: str, payload: contract, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return service.write(db, user.id, kind, payload, identity)

    def read(identity: str, revision: int | None = Query(default=None, ge=1),
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return service.describe(service.get(db, user.id, kind, identity, revision))

    def listing(user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0)):
        return [service.describe(row) for row in service.current(db, user.id, kind)[offset:offset+100]]

    router.add_api_route('/'+path, create, methods=['POST'], status_code=201, name='create_'+kind)
    router.add_api_route('/'+path, listing, methods=['GET'], name='list_'+kind)
    router.add_api_route('/'+path+'/{identity}', read, methods=['GET'], name='read_'+kind)
    router.add_api_route('/'+path+'/{identity}', edit, methods=['PUT'], name='edit_'+kind)


for path, kind, contract in (
    ('budgets', 'budget', contracts.BudgetWrite), ('obligations', 'obligation', contracts.ObligationWrite),
    ('obligation-settlements', 'settlement', contracts.SettlementWrite), ('receivables', 'receivable', contracts.ReceivableWrite),
    ('goals', 'goal', contracts.GoalWrite), ('debts', 'debt', contracts.DebtWrite)):
    register_resource(path, kind, contract)
