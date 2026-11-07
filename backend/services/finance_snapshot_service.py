"""Dashboard and Chat share the same explicitly dated ledger FinanceSnapshot.

Historical observed flows never establish positive investment capacity. Profile
values remain labelled declarations; reports never claim verified net worth.
"""
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.models.models import MonthlyReport
from backend.services.profile_service import ProfileService, snapshot_for, ProfileIncomplete
from backend.services import monthly_report_service as reports
from engines.cashflow import build_snapshot


def sources_changed(db, owner, snapshot):
    """Invalidate stored consumers when ledger appears or its source vector changes."""
    if not snapshot:
        return False
    source = snapshot.get('source_revision_vector', {})
    report_id = source.get('ledger_report_id')
    if report_id:
        return reports.read(db, owner, report_id)['stale']
    return db.query(MonthlyReport.id).filter_by(user_id=owner).first() is not None


def current_snapshot(db, owner):
    profile = ProfileService(db).get(owner)
    try:
        base = snapshot_for(profile) if profile else None
    except ProfileIncomplete:
        base = None
    report = db.query(MonthlyReport).filter_by(user_id=owner).order_by(
        MonthlyReport.month.desc(), MonthlyReport.created_at.desc(), MonthlyReport.id.desc()).first()
    if report is None:
        return base
    view = reports.read(db, owner, report.id)
    facts = report.snapshot['metrics']
    if base is None:
        base = build_snapshot({'income_paise': 0, 'expenses_paise': 0}, owner_id=owner)
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    historic = report.month != today.strftime('%Y-%m')
    verified = report.snapshot['selected_scope_complete'] and facts['classification_complete']
    labels = ['observed_ledger', 'household_inventory_unconfirmed']
    if historic:
        labels.append('historical_month')
    if view['stale']:
        labels.append('stale_sources')
    if not verified:
        labels.append('partial_or_unverified')
    reason = ('Observed ledger month ' + report.month + ' (' + ', '.join(labels) +
              '). Historical surplus does not establish future income, eligible liquid cash or investment capacity.')
    return replace(base, income_paise=facts['income_paise'], expenses_paise=facts['spending_paise'],
        surplus_paise=facts['recognized_surplus_paise'], shortfall_paise=facts['shortfall_paise'],
        flow_capacity_paise=None, available_contribution_paise=0 if facts['shortfall_paise'] else None,
        contribution_status='none' if facts['shortfall_paise'] else 'unavailable',
        contribution_reason=reason, status='partial', coverage=';'.join(labels), as_of=report.month,
        missing_inputs=list(dict.fromkeys(base.missing_inputs+['forward_flow', 'eligible_liquid_cash', 'household_inventory'])),
        metric_provenance={**base.metric_provenance, 'income': 'observed_ledger', 'expenses': 'observed_ledger',
                           'emergency_gap': 'profile_estimate_not_ledger_verified',
                           'available_contribution': 'unavailable_from_historical_surplus'},
        source_revision_vector={'profile_revision': base.profile_revision, 'ledger_report_id': report.id,
                                'accounts': report.vector, 'planning': report.snapshot.get('planning_vector', {})})
