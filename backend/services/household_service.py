"""Deterministic private books. No household data enters the advice/chat context."""
from uuid import uuid4
import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import HTTPException
from backend.core.config import config
from backend.core.money import check_paise
from backend.finance.ledger import atomic, lock_owner
from backend.models.models import (HouseholdRevision, Household, HouseholdMembership, HouseholdGrant, User, utcnow)


def missing():
    raise HTTPException(404, 'Resource not found.')


def house(db, identity):
    row = db.query(Household).filter_by(id=identity).first()
    if not row:
        missing()
    return row


def active_member(db, row, member):
    user = db.get(User, member)
    if not user or not user.is_active:
        return False
    return row.user_id == member or db.query(HouseholdMembership).filter_by(
        household_id=row.id, member_id=member, state='accepted').first() is not None


def locked_house(db, identity, actor, owner_only=False):
    enabled()
    row = house(db, identity)
    # All membership/grant mutations and reads use the same serializer.
    lock_house_owner(db, row.user_id)
    row = house(db, identity)
    if not active_member(db, row, actor) or (owner_only and row.user_id != actor):
        missing()
    return row


def lock_house_owner(db, owner):
    # Deactivated/held owners must look like missing households to recipients.
    # The shared lock service otherwise reports an unavailable owner as 409.
    try:
        lock_owner(db, owner, bump=False)
    except HTTPException as exc:
        if exc.status_code == 409:
            missing()
        raise


@atomic
def create_house(db, actor, payload):
    enabled()
    lock_owner(db, actor, bump=False)
    row = Household(id=str(uuid4()), user_id=actor, label=payload.label, revision=1)
    db.add(row)
    db.commit()
    return {'id': row.id, 'revision': row.revision, 'label': row.label,
            'role': 'owner', 'download_notice': 'Downloaded exports cannot be remotely recalled.'}


@atomic
def invite(db, actor, identity, payload):
    row = locked_house(db, identity, actor, owner_only=True)
    if row.revision != payload.expected_revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    if payload.member_id == actor or not db.query(User).filter_by(id=payload.member_id, is_active=True).first():
        missing()
    if db.query(HouseholdMembership).filter_by(household_id=identity, member_id=payload.member_id).first():
        raise HTTPException(409, 'Membership already exists; invitations cannot be replayed.')
    token = secrets.token_urlsafe(32)
    membership = HouseholdMembership(id=str(uuid4()), user_id=actor, household_id=identity,
        member_id=payload.member_id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=utcnow()+timedelta(hours=24), state='invited', revision=1)
    db.add(membership)
    row.revision += 1
    db.commit()
    return {'id': membership.id, 'token': token, 'expires_at': membership.expires_at,
            'household_revision': row.revision, 'revision': membership.revision}


@atomic
def accept(db, actor, invite_id, payload):
    enabled()
    row = db.query(HouseholdMembership).filter_by(id=invite_id, member_id=actor).first()
    if not row:
        missing()
    household = house(db, row.household_id)
    lock_house_owner(db, household.user_id)
    db.refresh(row)
    digest = hashlib.sha256(payload.token.get_secret_value().encode()).hexdigest()
    if row.state != 'invited' or row.expires_at <= utcnow() or not hmac.compare_digest(row.token_hash, digest):
        missing()
    row.state, row.revision = 'accepted', row.revision+1
    row.token_hash = ''  # consumed; never retain a usable invite
    household.revision += 1
    db.commit()
    return {'id': row.id, 'household_id': household.id, 'state': row.state, 'revision': row.revision}


@atomic
def grant(db, actor, identity, payload):
    household = locked_house(db, identity, actor)
    if actor == payload.member_id or not active_member(db, household, payload.member_id):
        missing()
    row = db.query(HouseholdGrant).filter_by(household_id=identity, user_id=actor,
                                            member_id=payload.member_id, view=payload.view).first()
    revision = row.revision if row else 0
    if payload.expected_revision != revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    if row is None:
        row = HouseholdGrant(id=str(uuid4()), user_id=actor, household_id=identity,
            member_id=payload.member_id, view=payload.view, revision=1, granted=payload.granted)
        db.add(row)
    else:
        row.revision += 1
        row.granted = payload.granted
    household.revision += 1
    db.commit()
    return {'id': row.id, 'view': row.view, 'granted': row.granted, 'revision': row.revision}


@atomic
def revoke_member(db, actor, identity, member_id, payload):
    household = locked_house(db, identity, actor)
    if actor not in (household.user_id, member_id) or member_id == household.user_id:
        missing()
    row = db.query(HouseholdMembership).filter_by(household_id=identity, member_id=member_id).first()
    if not row:
        missing()
    if row.revision != payload.expected_revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    row.state, row.revision, row.token_hash = 'revoked', row.revision+1, ''
    from sqlalchemy import or_
    for item in db.query(HouseholdGrant).filter(HouseholdGrant.household_id == identity,
            or_(HouseholdGrant.user_id == member_id, HouseholdGrant.member_id == member_id)):
        item.granted, item.revision = False, item.revision+1
    household.revision += 1
    db.commit()
    return {'state': row.state, 'revision': row.revision}


@atomic
def shared_view(db, actor, identity, source, view, expected_grant=None):
    household = locked_house(db, identity, actor)
    if not active_member(db, household, source) or view not in {'networth', 'protection'}:
        missing()
    permission = db.query(HouseholdGrant).filter_by(household_id=identity, user_id=source,
        member_id=actor, view=view, granted=True).first()
    if source != actor and permission is None:
        missing()
    if expected_grant is not None and (permission is None or permission.revision != expected_grant):
        missing()
    row = latest(db, source, view)
    if not row:
        missing()
    result = {**describe(row), 'household_revision': household.revision,
              'grant_revision': permission.revision if permission else None,
              'download_notice': 'Downloaded exports cannot be remotely recalled.'}
    if view == 'networth':
        result['snapshot'] = consolidate([row.data])
    db.commit()  # serialization ends only after the authorized response is materialized
    return result


@atomic
def request_export(db, actor, identity, source, view):
    """A queued reference contains no financial bytes; fetch always reauthorizes."""
    locked_house(db, identity, actor)
    permission = db.query(HouseholdGrant).filter_by(household_id=identity, user_id=source,
        member_id=actor, view=view, granted=True).first()
    if permission is None or not active_member(db, house(db, identity), source):
        missing()
    from backend.core.limits import reserve
    reserve(db, actor, 'exports', 1, config.EXPORT_DAILY_LIMIT)
    from backend.workers.queue import enqueue
    job = enqueue(db, actor, f'hx:{identity}:{permission.id}:{permission.revision}:{secrets.token_hex(6)}', 'household-export')
    db.commit()
    return {'id': job.id, 'state': 'queued', 'expires_seconds': config.EXPORT_TTL_SECONDS,
            'download_notice': 'Downloaded exports cannot be remotely recalled.'}


@atomic
def fetch_export(db, actor, identity):
    from backend.models.models import WorkItem
    enabled()
    job = db.query(WorkItem).filter_by(id=identity, user_id=actor, kind='household-export').first()
    if not job or job.created_at + timedelta(seconds=config.EXPORT_TTL_SECONDS) <= utcnow():
        missing()
    _, household_id, grant_id, revision, _ = job.event_key.split(':')
    permission = db.query(HouseholdGrant).filter_by(id=grant_id, member_id=actor).first()
    if permission is None:
        missing()
    return shared_view(db, actor, household_id, permission.user_id, permission.view, int(revision))


@atomic
def consolidated_view(db, actor, identity):
    household = locked_house(db, identity, actor)
    grants = db.query(HouseholdGrant).filter_by(household_id=identity, member_id=actor,
                                               view='networth', granted=True).all()
    owners = {actor: None}
    owners.update({g.user_id: g.revision for g in grants if active_member(db, household, g.user_id)})
    books, vector = [], {}
    for owner, grant_revision in sorted(owners.items()):
        row = latest(db, owner, 'networth')
        if row:
            books.append(row.data)
            vector[str(owner)] = {'book_revision': row.revision, 'grant_revision': grant_revision}
    result = {**consolidate(books), 'vector': vector, 'household_revision': household.revision,
              'allocation_status': 'unavailable', 'notice': 'Shared inventory is not spendable planning capacity.'}
    db.commit()
    return result


def enabled():
    if not getattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', False) or config.is_production_like:
        raise HTTPException(404, 'Resource not found.')


def latest(db, owner, kind, revision=None):
    query = db.query(HouseholdRevision).filter_by(user_id=owner, kind=kind)
    if revision is not None:
        query = query.filter_by(revision=revision)
    return query.order_by(HouseholdRevision.revision.desc()).first()


def describe(row):
    return {'id': row.id, 'revision': row.revision, 'kind': row.kind, 'data': row.data,
            'source': 'user_declared', 'status': 'partial'}


@atomic
def write(db, owner, kind, payload):
    enabled()
    lock_owner(db, owner, bump=False)
    request = {'kind': kind, **payload.model_dump(mode='json')}
    prior = db.query(HouseholdRevision).filter_by(user_id=owner, operation_key=payload.idempotency_key).first()
    if prior:
        if prior.request != request:
            raise HTTPException(409, 'Idempotency key reused with different input.')
        db.rollback()
        return describe(prior)
    current = latest(db, owner, kind)
    revision = current.revision if current else 0
    if payload.expected_revision != revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    data = payload.data.model_dump(mode='json')
    if kind == 'networth':
        consolidate([data])  # validate aggregate overflow before persistence
    row = HouseholdRevision(id=str(uuid4()), user_id=owner, kind=kind, revision=revision+1,
                            operation_key=payload.idempotency_key, request=request, data=data)
    db.add(row)
    db.flush()
    if kind == 'protection':
        from backend.services.notification_service import schedule
        from datetime import datetime, time
        for index, policy in enumerate(data['policies']):
            if policy['reminder_opt_in'] and not policy['archived']:
                when = datetime.combine(datetime.fromisoformat(policy['renewal_date']).date(), time(3, 30))
                schedule(db, owner, f'p:{row.id}:{index}', 'reminder', when)
    db.commit()
    return describe(row)


def consolidate(books):
    """Same identity requires identical facts; member shares may never exceed 100%."""
    references = {}
    for book in books:
        seen = set()
        for item in book['observations']:
            ref = item['reference']
            if ref in seen:
                continue
            seen.add(ref)
            facts = {k: v for k, v in item.items() if k != 'share_bps'}
            if ref in references:
                prior, shares = references[ref]
                if prior != facts or shares + item['share_bps'] > 10000:
                    raise HTTPException(409, 'Joint observation facts or shares conflict; review required.')
                references[ref] = (facts, shares + item['share_bps'])
            else:
                references[ref] = (facts, item['share_bps'])
    totals = {'asset': 0, 'liability': 0}
    for facts, shares in references.values():
        totals[facts['kind']] += facts['value_paise'] * shares // 10000
    for value in totals.values():
        check_paise(value)
    return {'assets_paise': totals['asset'] if references else None,
            'liabilities_paise': totals['liability'] if references else None,
            'net_worth_paise': check_paise(totals['asset']-totals['liability']) if references else None,
            'status': 'partial', 'coverage': 'declared_only', 'rule_version': 'networth.v1',
            'basis': 'included_observations_only',
            'missing_inputs': ['verified_account_inventory'] if references else ['declared_observations', 'verified_account_inventory'],
            'warnings': ['Unverified declared inventory; dates and account coverage may differ.',
                         'Do not add these observations to bank or portfolio totals.'],
            'observations': [{**facts, 'share_bps': shares} for facts, shares in references.values()]}
