"""Server-side entitlements (T1303). Plan comes from server state only; a client flag, header or query can never raise it.

Privacy, export and deletion are in every plan, including a downgraded or unknown one. No paid plan exists yet: the free pilot
grants every pilot feature and billing is disabled.
"""
from backend.core.config import config

ALWAYS = frozenset({'privacy_export', 'account_deletion', 'consent_controls', 'session_controls'})
CORE = frozenset({'profile', 'health', 'statements', 'monthly_report', 'manual_credit'})
PILOT = CORE | frozenset({'planning', 'portfolio', 'allocation_sandbox', 'tax_sandbox', 'household'})

PLANS = {'free_pilot': ALWAYS | PILOT, 'free': ALWAYS | CORE, 'suspended': ALWAYS}


def current_plan():
    return 'free_pilot' if config.BILLING_MODE == 'free_pilot' else 'suspended'


def capabilities(plan):
    return PLANS.get(plan, ALWAYS)          # unknown plan fails closed to the privacy floor


def entitled(feature, plan=None):
    return feature in capabilities(plan or current_plan())


def describe(plan=None):
    plan = plan or current_plan()
    return {'plan': plan, 'billing': 'disabled', 'paid_billing': 'deferred',
            'capabilities': sorted(capabilities(plan)), 'always_available': sorted(ALWAYS),
            'note': 'Free controlled pilot. No payment is requested or taken.'}
