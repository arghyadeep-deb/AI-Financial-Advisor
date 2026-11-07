"""Single owned observation boundary. No price feed, inference or orders."""
import csv
import io
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from pydantic import ValidationError
from backend.finance.ledger import atomic, lock_owner
from backend.core.money import check_paise
from backend.core.telemetry import traceable
from backend.models.models import PortfolioRevision
from backend.schemas.portfolio import Holdings, Observation
from engines.portfolio import Position, metrics, shock


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def get(db, owner, kind, revision=None):
    q = db.query(PortfolioRevision).filter_by(user_id=owner, kind=kind)
    if revision is not None:
        q = q.filter_by(revision=revision)
    row = q.order_by(PortfolioRevision.revision.desc()).first()
    if row is None:
        raise HTTPException(404, 'Portfolio resource not found.')
    return row


def describe(row):
    return {'id': row.id, 'kind': row.kind, 'revision': row.revision,
            'data': row.data, 'created_at': row.created_at.isoformat()}


@atomic
@traceable(name='portfolio_revision')
def write(db, owner, kind, payload):
    lock_owner(db, owner, bump=False)
    request = {'kind': kind, **payload.model_dump(mode='json')}
    prior = db.query(PortfolioRevision).filter_by(user_id=owner, operation_key=payload.idempotency_key).first()
    if prior:
        if prior.request != request:
            raise HTTPException(409, 'Idempotency key reused with different input.')
        db.rollback()
        return describe(prior)
    before = db.query(PortfolioRevision).filter_by(user_id=owner, kind=kind).order_by(PortfolioRevision.revision.desc()).first()
    revision = before.revision if before else 0
    if revision != payload.expected_revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    data = payload.data.model_dump(mode='json')
    if kind == 'holdings':
        if payload.data.as_of > today():
            raise HTTPException(422, 'Future holdings require review; cannot confirm as observed.')
        # Validate aggregate arithmetic before storing. Missing quotes remain missing.
        valuation_data(data, today())
    elif kind == 'suitability':
        if data['revision'] != revision + 1:
            raise HTTPException(422, 'Answer revision must equal the next stored revision.')
    else:
        raise ValueError('Unsupported portfolio document')
    row = PortfolioRevision(id=str(uuid4()), user_id=owner, kind=kind, revision=revision+1,
        operation_key=payload.idempotency_key, request=request, data=data)
    db.add(row)
    db.commit()
    return describe(row)


def valuation_data(data, as_of):
    book = Holdings.model_validate(data)
    positions = tuple(Position(observation_id=str(i), account_ref=p.account_ref, instrument_id=p.instrument_id,
        issuer_id=p.issuer_id, asset_class=p.asset_class, currency=p.currency, units=Decimal(p.units),
        price_paise=p.price_paise, price_date=p.price_date, source_id=p.price_source,
        source_version=p.price_version, expires=p.price_expires, cost_basis_paise=p.cost_basis_paise,
        corporate_actions_supported=p.corporate_actions_supported)
        for i, p in enumerate(book.observations) if not p.closed)
    result = metrics(positions, as_of=as_of)
    if not positions and book.inventory_complete:
        # Explicitly confirmed empty/closed inventory is distinct from a missing price.
        result.update(status='complete', total_value_paise=0, known_subtotal_paise=0)
    stale = book.as_of != as_of
    dated = metrics(positions, as_of=book.as_of) if stale else result
    if stale and not positions and book.inventory_complete:
        dated = {**dated, 'total_value_paise': 0}
    # User confirmation is a declaration, never independent price/ownership verification.
    return {**result, 'dated_total_value_paise': dated['total_value_paise'],
        'total_value_paise': None if stale else result['total_value_paise'],
        'status': 'partial' if stale else result['status'],
        'observation_date': book.as_of.isoformat(), 'stale': stale,
        'verification': 'owner_confirmed_unverified', 'inventory_complete_declared': book.inventory_complete,
        'coverage': ['owner_confirmed_unverified'] + (['stale_observations'] if stale else []) +
                    ([] if book.inventory_complete else ['inventory_incomplete']),
        'verified_net_worth_eligible': False,
        'concentration_method': 'Issuer HHI=sum((issuer value/priced value)^2); unknown issuer separately labelled.',
        'observations': data['observations']}


def valuation(db, owner, as_of=None, revision=None):
    day = as_of or today()
    if day > today():
        raise HTTPException(422, 'Future valuation date unsupported.')
    row = get(db, owner, 'holdings', revision)
    if date.fromisoformat(row.data['as_of']) > day:
        raise HTTPException(422, 'Observation postdates requested valuation.')
    return {'holdings_revision': row.revision, **valuation_data(row.data, day)}


def scenario(db, owner, payload):
    current = get(db, owner, 'holdings')
    if current.revision != payload.expected_revision:
        raise HTTPException(409, 'Holdings changed; reload before retrying.')
    observed = valuation(db, owner, payload.as_of, revision=current.revision)
    from backend.services.finance_snapshot_service import current_snapshot
    finance = current_snapshot(db, owner)
    cap = None if finance is None else finance.available_contribution_paise
    value = observed['total_value_paise']
    return {'status': 'hypothetical', 'persisted': False, 'holdings_revision': current.revision,
        'observed': observed, 'shock_bps': payload.shock_bps,
        'shock': None if value is None else shock(value, payload.shock_bps),
        'chosen_contribution_paise': payload.contribution_paise,
        'scenario_value_with_contribution_paise': None if value is None else
            check_paise(
                shock(value, payload.shock_bps)['scenario_value_paise'] + payload.contribution_paise),
        'verified_affordable_contribution_paise': 0 if finance and finance.shortfall_paise else None,
        'declared_contribution_cap_paise': cap,
        'affordability': 'unavailable: observations/profile do not verify forward capacity',
        'public_eligible': False, 'named_products_eligible': False}


# Text-only import preview, no file storage or parser/worker bypass. Confirmation uses write().
CSV_COLUMNS = ('account_ref', 'instrument_id', 'units', 'observation_date', 'asset_class', 'issuer_id',
               'price_paise', 'price_date', 'price_source', 'price_version', 'price_expires', 'cost_basis_paise')


@traceable(name='portfolio_csv_preview')
def csv_preview(payload):
    reader = csv.DictReader(io.StringIO(payload.csv_text), strict=True)
    try:
        header = tuple(reader.fieldnames or ())
    except csv.Error as exc:
        raise HTTPException(422, 'Unsupported holdings CSV header.') from exc
    if header != CSV_COLUMNS:
        raise HTTPException(422, 'Unsupported holdings CSV header.')
    rows = []
    try:
        for row in reader:
            if len(rows) >= 500 or None in row or any(v is None for v in row.values()):
                raise ValueError('CSV row limit or width invalid')
            data = {k: v for k, v in row.items() if v != ''}
            for k in ('price_paise', 'price_version', 'cost_basis_paise'):
                if k in data:
                    data[k] = int(data[k])
            rows.append(Observation.model_validate(data))
        book = Holdings(confirmed=True, source='csv', as_of=payload.as_of, observations=rows)
    except (ValueError, ValidationError, csv.Error) as exc:
        raise HTTPException(422, 'CSV requires review: invalid or overlapping observations.') from exc
    preview = book.model_dump(mode='json')
    preview.pop('confirmed')  # A preview cannot grant its own owner confirmation.
    return {'status': 'requires_owner_confirmation', 'persisted': False, 'preview': preview}
