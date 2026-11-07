"""Operator CLI metadata only. No public metrics endpoint or external exporter."""
from sqlalchemy import text, func
from backend.models.models import WorkItem, StatementImport, MonthlyReport, LoginThrottle, utcnow
from backend.workers.queue import metrics


def snapshot(db, stale_seconds=300):
    db.execute(text('SELECT 1'))
    oldest = db.query(func.min(WorkItem.created_at)).filter(WorkItem.state.in_(['queued', 'running'])).scalar()
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


def emit(db, exporter):
    """An optional metadata exporter cannot mutate or fail a ledger transaction."""
    result = snapshot(db)
    try:
        exporter(result)
    except Exception:
        return {'exporter': 'unavailable'}
    return {'exporter': 'ok'}
