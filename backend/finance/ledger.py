"""Single exact-money ledger owner. Evidence survives overlap/reversal; no LLM writes."""
from functools import wraps
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import update, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from backend.core.money import check_paise
from backend.models.models import (User, StatementAccount, StatementImport, StatementRow, WorkItem,
    LedgerEntry, LedgerEvidence, LedgerCorrection, LedgerLink)
from backend.services.statement_service import owned, describe


def atomic(fn):
    @wraps(fn)
    def run(db, *args, **kwargs):
        try:
            return fn(db, *args, **kwargs)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, 'Concurrent operation changed the resource; reload and retry.') from exc
        except OperationalError as exc:
            db.rollback()
            if 'locked' in str(exc.orig).lower() or 'deadlock' in str(exc.orig).lower():
                raise HTTPException(409, 'Concurrent operation; reload and retry.') from exc
            raise
        except Exception:
            db.rollback()
            raise
    return run


def lock_owner(db, owner, bump=True):
    """Serialize owner's account/link mutations in stable order on SQLite and PG."""
    user = db.query(User).filter_by(id=owner).with_for_update().first()
    if not user or not user.is_active:
        raise HTTPException(409, 'Account unavailable.')
    # SQLite ignores FOR UPDATE. Acquire its write reservation even for owners
    # with no statement accounts (planning revisions share this serialization).
    guard = db.execute(update(User).where(User.id == owner, User.is_active.is_(True)).values(id=User.id))
    if guard.rowcount != 1:
        raise HTTPException(409, 'Account unavailable.')
    ids = [row[0] for row in db.query(StatementAccount.id).filter_by(user_id=owner).order_by(StatementAccount.id)]
    for identity in ids:
        db.execute(update(StatementAccount).where(StatementAccount.id == identity,
            StatementAccount.user_id == owner).values(revision=StatementAccount.revision + (1 if bump else 0)))
    db.expire_all()


def replay(db, owner, target, kind, payload):
    data = {'operation': kind, 'target': target, **payload.model_dump(mode='json')}
    existing = db.query(LedgerCorrection).filter_by(user_id=owner, operation_key=payload.idempotency_key).first()
    if existing:
        if existing.payload != data:
            raise HTTPException(409, 'Idempotency key reused with different input.')
        return data, existing.after
    return data, None


def audit(db, owner, account_id, target, payload, before, after):
    db.add(LedgerCorrection(id=str(uuid4()), user_id=owner, account_id=account_id, target_id=target,
        operation_key=payload['idempotency_key'], payload=payload, before=before, after=after))


def expect(row, revision):
    if row.revision != revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')


def source_rows(db, owner, import_id):
    return db.query(StatementRow).filter_by(user_id=owner, import_id=import_id).order_by(StatementRow.ordinal).all()


def candidates(db, owner, job):
    """Candidates do not change totals. Stable refs still require identical facts."""
    entries = db.query(LedgerEntry).filter_by(user_id=owner, account_id=job.account_id, active=True).all()
    output = {}
    for row in source_rows(db, owner, job.id):
        matches = [e.id for e in entries if (row.reference and row.reference == e.reference)
            or (not row.reference and (e.posting_date, e.amount_paise, e.description) ==
                (row.posting_date, row.amount_paise, row.description))]
        if matches:
            output[row.id] = matches
    return output


@atomic
def publish(db, owner, import_id, payload):
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'publish', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'publish', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(job, payload.expected_revision)
    if job.state != 'needs_review' or job.error_code in {'balance_mismatch', 'account_mismatch'}:
        raise HTTPException(409, 'Import is not publishable; replace mismatched source data.')
    if job.difference_paise is None and not payload.acknowledge_unverified:
        raise HTTPException(409, 'Explicit acknowledgement of unverified balances is required.')
    rows = source_rows(db, owner, job.id)
    if not rows:
        raise HTTPException(409, 'No staged rows.')
    decisions = {r.row_id: r for r in payload.decisions}
    if len(decisions) != len(payload.decisions) or set(decisions) - {r.id for r in rows}:
        raise HTTPException(422, 'Review contains duplicate or unknown rows.')
    existing = db.query(LedgerEntry).filter_by(user_id=owner, account_id=job.account_id, active=True).all()
    before = describe(job)
    for row in rows:
        decision = decisions.get(row.id)
        category = decision.category if decision else row.category
        from backend.schemas.statements import Component
        try:
            component = Component(category=category, amount_paise=row.amount_paise).model_dump()
        except ValueError as exc:
            raise HTTPException(422, 'Classification direction conflicts with source money.') from exc
        match = None
        references = [entry for entry in existing if row.reference and entry.reference == row.reference]
        if references:
            if len(references) != 1 or (references[0].amount_paise, references[0].posting_date) != (row.amount_paise, row.posting_date):
                raise HTTPException(409, 'Stable reference conflicts with existing facts.')
            match = references[0]
            if decision and (decision.distinct or decision.match_entry_id not in (None, match.id)):
                raise HTTPException(409, 'Stable reference cannot be made distinct.')
        elif decision and decision.match_entry_id:
            match = owned(db, LedgerEntry, owner, decision.match_entry_id)
            if not match.active or (match.account_id, match.posting_date, match.amount_paise) != (job.account_id, row.posting_date, row.amount_paise):
                raise HTTPException(422, 'Match facts differ.')
            if row.reference and match.reference and row.reference != match.reference:
                raise HTTPException(422, 'Different stable references identify distinct transactions.')
        elif not row.reference and not (decision and decision.distinct):
            ambiguous = [entry for entry in existing if (entry.posting_date, entry.amount_paise, entry.description) ==
                         (row.posting_date, row.amount_paise, row.description)]
            if ambiguous:
                raise HTTPException(409, {'code': 'overlap_review', 'message': 'Confirm a match or a distinct transaction.', 'row_id': row.id})
        if match is None:
            match = LedgerEntry(id=str(uuid4()), user_id=owner, account_id=job.account_id,
                posting_date=row.posting_date, amount_paise=row.amount_paise, description=row.description,
                reference=row.reference, components=[component])
            db.add(match)
            db.flush()
        elif decision and match.components != [component]:
            raise HTTPException(409, 'Matched entry already has a classification; use its revision-checked split API to correct it.')
        db.add(LedgerEvidence(id=str(uuid4()), user_id=owner, entry_id=match.id, row_id=row.id, import_id=job.id))
    job.state, job.checkpoint = 'completed', 'published'
    job.business_commit_id = str(uuid4())
    job.revision += 1
    result = describe(job)
    audit(db, owner, job.account_id, job.id, data, before, result)
    from backend.services.notification_service import schedule
    from backend.models.models import utcnow
    schedule(db, owner, job.id, 'reminder', utcnow())
    db.commit()
    return result


def invalidate_links(db, owner, removed):
    if not removed:
        return
    links = db.query(LedgerLink).filter(LedgerLink.user_id == owner, LedgerLink.active.is_(True),
        or_(LedgerLink.left_id.in_(removed), LedgerLink.right_id.in_(removed))).all()
    for link in links:
        link.active = False
        if link.kind == 'manual_match' and link.left_id in removed:
            # Reversing the last bank evidence restores the retained manual origin.
            owned(db, LedgerEntry, owner, link.right_id).active = True
    if links:
        # confirm_link/reverse_link advance both endpoints. Evidence reversal
        # must also fence stale edits on surviving counterpart transactions.
        # Removed endpoints already advanced in reverse; bump each survivor once.
        survivors = {identity for link in links for identity in (link.left_id, link.right_id)} - set(removed)
        for identity in sorted(survivors):
            entry = owned(db, LedgerEntry, owner, identity)
            entry.revision += 1
        bump_links(db, owner)
    # All owner revisions already advance under lock, including counterpart accounts.


def bump_links(db, owner):
    db.execute(update(StatementAccount).where(StatementAccount.user_id == owner).values(
        link_revision=StatementAccount.link_revision + 1))


@atomic
def reverse(db, owner, import_id, payload):
    owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'reverse', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'reverse', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(job, payload.expected_revision)
    if job.state != 'completed':
        raise HTTPException(409, 'Only a completed import can be reversed.')
    before, removed = describe(job), []
    evidence = db.query(LedgerEvidence).filter_by(user_id=owner, import_id=job.id, active=True).all()
    for support in evidence:
        support.active = False
    db.flush()
    for entry_id in {support.entry_id for support in evidence}:
        if not db.query(LedgerEvidence).filter_by(user_id=owner, entry_id=entry_id, active=True).count():
            entry = owned(db, LedgerEntry, owner, entry_id)
            entry.active = False
            entry.revision += 1
            removed.append(entry_id)
    invalidate_links(db, owner, removed)
    job.state, job.checkpoint = 'reversed', 'reversed'
    job.revision += 1
    result = {**describe(job), 'inactive_entry_ids': sorted(removed)}
    audit(db, owner, job.account_id, job.id, data, before, result)
    db.commit()
    return result


@atomic
def cancel(db, owner, import_id, payload):
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'cancel', payload)
    if prior is not None:
        return prior
    # Same work -> account lock order as queue.complete; stale worker is fenced out.
    db.execute(update(WorkItem).where(WorkItem.id == job.work_id, WorkItem.user_id == owner,
        WorkItem.state.in_(['queued', 'running'])).values(state='cancelled', fence=WorkItem.fence + 1))
    lock_owner(db, owner)
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'cancel', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(job, payload.expected_revision)
    if job.state not in {'queued', 'needs_review', 'quarantined'}:
        raise HTTPException(409, 'Import has completed; use reversal.')
    before = describe(job)
    job.state, job.checkpoint = 'cancelled', 'cancelled'
    job.revision += 1
    result = describe(job)
    audit(db, owner, job.account_id, job.id, data, before, result)
    db.commit()
    return result


@atomic
def reprocess(db, owner, import_id, payload):
    from backend.workers.queue import enqueue
    from backend.core.config import config
    from backend.core.limits import reserve
    owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'reprocess', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    job = owned(db, StatementImport, owner, import_id)
    data, prior = replay(db, owner, import_id, 'reprocess', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(job, payload.expected_revision)
    if job.state not in {'reversed', 'cancelled', 'quarantined'}:
        raise HTTPException(409, 'Reverse completed import before reprocessing.')
    latest = db.query(StatementImport).filter_by(user_id=owner, document_id=job.document_id).order_by(StatementImport.generation.desc()).first()
    if latest.id != job.id:
        raise HTTPException(409, 'A later generation already exists.')
    from backend.services.statement_service import read_document
    read_document(db, owner, job.document_id)  # expiry/key checks before reserving work
    reserve(db, owner, 'jobs', 1, config.UPLOAD_DAILY_LIMIT)
    generation = job.generation + 1
    work = enqueue(db, owner, 'statement:' + job.document_id + ':' + str(generation), 'statement')
    from backend.finance.importers.registry import PARSER_VERSION
    new = StatementImport(id=str(uuid4()), user_id=owner, account_id=job.account_id,
        document_id=job.document_id, work_id=work.id, generation=generation, parser_version=PARSER_VERSION)
    db.add(new)
    db.flush()
    result = describe(new)
    audit(db, owner, job.account_id, job.id, data, describe(job), result)
    db.commit()
    return result


@atomic
def split(db, owner, entry_id, payload):
    owned(db, LedgerEntry, owner, entry_id)
    data, prior = replay(db, owner, entry_id, 'split', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    entry = owned(db, LedgerEntry, owner, entry_id)
    data, prior = replay(db, owner, entry_id, 'split', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(entry, payload.expected_revision)
    if not entry.active or sum(c.amount_paise for c in payload.components) != entry.amount_paise or any(
            (c.amount_paise > 0) != (entry.amount_paise > 0) for c in payload.components):
        raise HTTPException(422, 'Components must conserve signed paise exactly.')
    if db.query(LedgerLink).filter(LedgerLink.user_id == owner, LedgerLink.active.is_(True),
            or_(LedgerLink.left_id == entry.id, LedgerLink.right_id == entry.id)).count():
        raise HTTPException(409, 'Linked transactions require link reversal before classification changes.')
    before = {'components': entry.components, 'revision': entry.revision}
    for component in payload.components:
        if component.obligation_id:
            from backend.services.planning_service import get
            obligation = get(db, owner, 'obligation', component.obligation_id)
            if obligation.data['archived'] or obligation.data['paused']:
                raise HTTPException(422, 'Split references an inactive obligation.')
    entry.components = [c.model_dump() for c in payload.components]
    entry.revision += 1
    result = {'id': entry.id, 'components': entry.components, 'revision': entry.revision}
    audit(db, owner, entry.account_id, entry.id, data, before, result)
    db.commit()
    return result


@atomic
def confirm_link(db, owner, payload):
    left = owned(db, LedgerEntry, owner, payload.left_id)
    right = owned(db, LedgerEntry, owner, payload.right_id)
    data, prior = replay(db, owner, left.id, 'link', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    left = owned(db, LedgerEntry, owner, payload.left_id)
    right = owned(db, LedgerEntry, owner, payload.right_id)
    data, prior = replay(db, owner, left.id, 'link', payload)
    if prior is not None:
        db.rollback()
        return prior
    expect(left, payload.expected_revision)
    expect(right, payload.expected_right_revision)
    if not left.active or not right.active or left.id == right.id or left.amount_paise >= 0 or right.amount_paise <= 0:
        raise HTTPException(422, 'A link requires active debit and credit evidence.')
    amount = payload.amount_paise
    if payload.kind in {'transfer', 'card_settlement'}:
        if left.account_id == right.account_id or amount != -left.amount_paise or amount != right.amount_paise:
            raise HTTPException(422, 'Transfer requires two different owned accounts and equal amounts.')
    elif right.posting_date < left.posting_date:
        raise HTTPException(422, 'Adjustment precedes purchase.')
    if payload.kind in {'refund', 'reimbursement'} and any(c['category'] not in {'purchase', 'fee', 'interest'} for c in left.components):
        raise HTTPException(422, 'Adjustment requires an eligible purchase.')
    if payload.kind == 'reimbursement':
        from backend.services.planning_service import active_rows
        for receivable in active_rows(db, owner, 'receivable'):
            if receivable.data['purchase_entry_id'] == left.id:
                received = sum(l.amount_paise for l in db.query(LedgerLink).filter_by(
                    user_id=owner, left_id=left.id, kind='reimbursement', active=True))
                if received+amount > receivable.data['due_paise']:
                    raise HTTPException(422, 'Reimbursement exceeds confirmed receivable.')
    for entry in (left, right):
        existing = db.query(LedgerLink).filter(LedgerLink.user_id == owner, LedgerLink.active.is_(True),
                or_(LedgerLink.left_id == entry.id, LedgerLink.right_id == entry.id)).all()
        if any(link.kind != payload.kind for link in existing) or sum(link.amount_paise for link in existing) + amount > abs(entry.amount_paise):
            raise HTTPException(422, 'Link exceeds remaining eligible amount or conflicts with another link.')
    link = LedgerLink(id=str(uuid4()), user_id=owner, left_id=left.id, right_id=right.id,
        kind=payload.kind, amount_paise=amount)
    db.add(link)
    bump_links(db, owner)
    left.revision += 1
    right.revision += 1
    result = {'id': link.id, 'kind': link.kind, 'amount_paise': amount, 'revision': left.revision}
    audit(db, owner, left.account_id, left.id, data, {}, result)
    db.commit()
    return result


@atomic
def reverse_link(db, owner, link_id, payload):
    owned(db, LedgerLink, owner, link_id)
    data, prior = replay(db, owner, link_id, 'reverse_link', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner)
    link = owned(db, LedgerLink, owner, link_id)
    data, prior = replay(db, owner, link_id, 'reverse_link', payload)
    if prior is not None:
        db.rollback()
        return prior
    left = owned(db, LedgerEntry, owner, link.left_id)
    right = owned(db, LedgerEntry, owner, link.right_id)
    expect(left, payload.expected_revision)
    if not link.active:
        raise HTTPException(409, 'Link is already inactive.')
    if link.kind == 'manual_match':
        raise HTTPException(409, 'Reverse bank evidence to restore a matched manual origin.')
    link.active = False
    bump_links(db, owner)
    left.revision += 1
    right.revision += 1
    result = {'id': link.id, 'active': False, 'revision': left.revision}
    audit(db, owner, left.account_id, link.id, data, {'active': True}, result)
    db.commit()
    return result


def manual_enabled():
    from backend.core.config import config
    if not config.SYNTHETIC_MANUAL_CASH_ENABLED or config.is_production_like:
        raise HTTPException(404, 'Resource not found.')


@atomic
def manual_cash(db, owner, payload):
    manual_enabled()
    owned(db, StatementAccount, owner, payload.account_id)
    data, prior = replay(db, owner, payload.account_id, 'manual_cash', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner, bump=False)
    data, prior = replay(db, owner, payload.account_id, 'manual_cash', payload)
    if prior is not None:
        db.rollback()
        return prior
    account = owned(db, StatementAccount, owner, payload.account_id)
    expect(account, payload.expected_revision)
    if account.account_type != 'synthetic_cash':
        raise HTTPException(422, 'Manual cash requires a separate cash account.')
    from backend.schemas.statements import Component
    entry = LedgerEntry(id=str(uuid4()), user_id=owner, account_id=account.id,
        posting_date=payload.posting_date.isoformat(), amount_paise=payload.amount_paise,
        description=payload.description, origin='manual_cash', components=[
            Component(category=payload.category, amount_paise=payload.amount_paise).model_dump()])
    db.add(entry)
    db.flush()
    account.revision += 1
    result = {'id': entry.id, 'account_id': account.id, 'account_revision': account.revision,
              'revision': entry.revision, 'origin': entry.origin, 'amount_paise': entry.amount_paise}
    audit(db, owner, account.id, entry.id, data, {}, result)
    db.commit()
    return result


@atomic
def match_manual(db, owner, bank_id, payload):
    manual_enabled()
    owned(db, LedgerEntry, owner, bank_id)
    owned(db, LedgerEntry, owner, payload.manual_entry_id)
    data, prior = replay(db, owner, bank_id, 'manual_match', payload)
    if prior is not None:
        return prior
    lock_owner(db, owner, bump=False)
    data, prior = replay(db, owner, bank_id, 'manual_match', payload)
    if prior is not None:
        db.rollback()
        return prior
    bank = owned(db, LedgerEntry, owner, bank_id)
    manual = owned(db, LedgerEntry, owner, payload.manual_entry_id)
    expect(bank, payload.expected_revision)
    expect(manual, payload.expected_manual_revision)
    if (not bank.active or not manual.active or bank.origin != 'bank' or manual.origin != 'manual_cash'
            or bank.amount_paise >= 0 or (bank.posting_date, bank.amount_paise) != (manual.posting_date, manual.amount_paise)
            or bank.components != manual.components
            or any(c['category'] not in {'purchase', 'fee', 'interest'} for c in bank.components)):
        raise HTTPException(422, 'Match requires identical dated spending and explicit classification review.')
    if not db.query(LedgerEvidence).filter_by(user_id=owner, entry_id=bank.id, active=True).first():
        raise HTTPException(422, 'Active bank source evidence required.')
    if db.query(LedgerLink).filter(LedgerLink.user_id == owner, LedgerLink.active.is_(True),
            or_(LedgerLink.left_id.in_([bank.id, manual.id]), LedgerLink.right_id.in_([bank.id, manual.id]))).first():
        raise HTTPException(409, 'Linked origins require review before matching.')
    # Keep both rows and correction evidence; only the bank origin remains in totals.
    manual.active = False
    manual.revision += 1
    bank.revision += 1
    link = LedgerLink(id=str(uuid4()), user_id=owner, left_id=bank.id, right_id=manual.id,
                      kind='manual_match', amount_paise=-bank.amount_paise)
    db.add(link)
    bump_links(db, owner)
    db.flush()
    result = {'id': link.id, 'bank_entry_id': bank.id, 'manual_entry_id': manual.id,
              'revision': bank.revision, 'manual_revision': manual.revision}
    audit(db, owner, bank.account_id, bank.id, data, {'manual_active': True}, result)
    db.commit()
    return result


def metrics(entries, links=()):
    """Observed flows only. Affordability needs prospective coverage and stays unavailable."""
    result = {key: 0 for key in ('income_paise', 'spending_paise', 'cash_movement_paise', 'borrowing_paise',
        'investment_paise', 'disposal_paise', 'principal_paise', 'unsplit_debt_paise', 'refund_paise',
        'reimbursement_paise', 'unclassified_credit_paise', 'unclassified_debit_paise')}
    complete = True
    for entry in entries:
        if not entry.active:
            continue
        amount = entry.amount_paise
        result['cash_movement_paise'] = check_paise(result['cash_movement_paise'] + amount)
        incoming = [link for link in links if link.active and link.right_id == entry.id]
        outgoing = [link for link in links if link.active and link.left_id == entry.id]
        movement = [link for link in incoming + outgoing if link.kind in {'transfer', 'card_settlement'}]
        if movement:
            continue  # explicit confirmed two-sided movement
        adjustments = [link for link in incoming if link.kind in {'refund', 'reimbursement'}]
        adjusted = sum(link.amount_paise for link in adjustments)
        for link in adjustments:
            key = 'refund_paise' if link.kind == 'refund' else 'reimbursement_paise'
            result[key] += link.amount_paise
            if link.kind == 'refund':
                result['spending_paise'] -= link.amount_paise
        if adjusted:
            # Remaining credit is unresolved; never treat leftover as salary.
            remainder = amount - adjusted
            result['unclassified_credit_paise'] += remainder
            complete = complete and remainder == 0
            continue
        for component in entry.components:
            category, value = component['category'], component['amount_paise']
            if category == 'income': result['income_paise'] += value
            elif category in {'purchase', 'fee', 'interest'}: result['spending_paise'] -= value
            elif category == 'borrowing': result['borrowing_paise'] += value
            elif category == 'investment': result['investment_paise'] -= value
            elif category == 'disposal': result['disposal_paise'] += value
            elif category == 'loan_principal': result['principal_paise'] -= value
            elif category == 'unsplit_debt':
                result['unsplit_debt_paise'] -= value
                complete = False
            else:
                result['unclassified_credit_paise' if value > 0 else 'unclassified_debit_paise'] += abs(value)
                complete = False  # unlinked transfers/refunds/withdrawals remain unresolved
    for value in result.values():
        check_paise(value)
    surplus = check_paise(result['income_paise'] - result['spending_paise'])
    return {**result, 'recognized_surplus_paise': surplus, 'shortfall_paise': max(0, -surplus),
        'classification_complete': complete, 'eligible_contribution_paise': 0 if surplus < 0 else None,
        'affordability_status': 'deficit' if surplus < 0 else 'unavailable',
        'affordability_reason': 'prospective_flow_liquidity_and_obligations_not_verified'}
