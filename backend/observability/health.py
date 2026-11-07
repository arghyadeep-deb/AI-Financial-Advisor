"""Operator CLI metadata only. No public metrics endpoint or external exporter."""
from sqlalchemy import text, func
from backend.models.models import WorkItem, StatementImport, MonthlyReport, LoginThrottle, utcnow
from backend.workers.queue import metrics


def snapshot(db, stale_seconds=300):
    db.execute(text('SELECT 1'))
    oldest = db.query(func.min(WorkItem.available_at)).filter(WorkItem.state.in_(['queued', 'running']), WorkItem.available_at <= utcnow()).scalar()
    age = max(0, int((utcnow() - oldest).total_seconds())) if oldest else 0
    counts = metrics(db)
    alerts = []
    if age > stale_seconds:
        alerts.append({'code': 'queue_stale', 'severity': 'warning', 'action': 'inspect worker leases'})
    if counts.get('dead_letter', 0):
        alerts.append({'code': 'work_exhausted', 'severity': 'warning', 'action': 'inspect bounded retries'})
    mismatches = db.query(StatementImport).filter_by(error_code='balance_mismatch', state='needs_review').count()
    partial = db.query(MonthlyReport).filter(MonthlyReport.snapshot['selected_scope_complete'].as_boolean().is_(False)).count()
    locked = db.query(LoginThrottle).filter(LoginThrottle.locked_until > utcnow()).count()
    if mismatches:
        alerts.append({'code': 'reconciliation_blocked', 'severity': 'warning', 'action': 'inspect parser version; keep publication blocked'})
    if locked:
        alerts.append({'code': 'auth_throttled', 'severity': 'warning', 'action': 'inspect aggregate abuse counters'})
    from backend.core.telemetry import events
    durations = sorted(event['duration_ms'] for event in events)
    p95 = durations[min(len(durations)-1, (95*len(durations)+99)//100-1)] if durations else None
    return {'database_ready': True, 'queue': counts, 'oldest_work_seconds': age,
        'blocked_reconciliations': mismatches, 'partial_reports': partial, 'locked_auth_buckets': locked,
        'recent_span_p95_ms': p95, 'paid_model_cost': 'unavailable_disabled', 'alerts': alerts}


def readiness(db, required_workers=('notifications', 'statements', 'retention'), journal=None):
    """Operator-only fail-closed readiness. Never returns DB errors or locations."""
    from backend.core.config import config
    from backend.core.operations import WORKERS
    from backend.models.models import OperationalCounter
    if not set(required_workers) <= WORKERS:
        raise ValueError('Unsupported worker')
    try:
        result = snapshot(db)
        stale = []
        for worker in required_workers:
            row = db.get(OperationalCounter, ('worker:' + worker, 'current'))
            age = (utcnow() - row.updated_at).total_seconds() if row else None
            if age is None or not 0 <= age <= config.WORKER_STALE_SECONDS:
                stale.append(worker)
        result.update(ready=not stale, stale_workers=stale)
        if stale:
            result['alerts'].append({'code': 'worker_stale', 'severity': 'critical',
                'action': 'restart worker; inspect supervisor', 'owner': 'operations'})
        if journal:
            lag = journal.deletion_lag_seconds()
            result['deletion_lag_seconds'] = lag
            if lag > config.WORKER_STALE_SECONDS:
                result['alerts'].append({'code': 'deletion_stale', 'severity': 'critical',
                    'action': 'resume suppressed deletion; inspect holds', 'owner': 'privacy_operations'})
        for alert in result['alerts']:
            alert.setdefault('owner', 'operations')
        cost = db.get(OperationalCounter, ('model_cost_paise', utcnow().date().isoformat()))
        result['reserved_model_cost_paise'] = cost.used if cost else 0
        return result
    except Exception:
        db.rollback()
        return {'ready': False, 'database_ready': False, 'alerts': [{'code': 'dependency_unavailable',
            'severity': 'critical', 'owner': 'operations', 'action': 'inspect DB/journal connectivity; keep traffic closed'}]}


def emit(db, exporter):
    """An optional metadata exporter cannot mutate or fail a ledger transaction."""
    result = snapshot(db)
    try:
        exporter(result)
    except Exception:
        return {'exporter': 'unavailable'}
    return {'exporter': 'ok'}


if __name__ == '__main__':
    import json
    from backend.core.database import SessionLocal
    from backend.services.privacy.lifecycle import configured_journal
    with SessionLocal() as db:
        result = readiness(db, journal=configured_journal())
        print(json.dumps(result))
        raise SystemExit(0 if result['ready'] else 1)
