"""Test-only in-memory bank. Refuses to exist outside the synthetic sandbox; contains no real provider behaviour."""
from backend.core.config import config
from backend.integrations.base import ProviderRejected, ProviderTimeout


class FakeBank:
    name = 'fake-bank'

    def __init__(self, events=None, *, submit_mode='ok', status_script=None, before_return=None):
        if not config.SYNTHETIC_STATEMENTS_ENABLED or config.is_production_like:
            raise RuntimeError('The fake bank only exists in the synthetic sandbox.')
        self.events = list(events or [])
        self.submit_mode = submit_mode          # ok | reject | timeout_after_apply | timeout_before_apply
        self.applied = {}                       # operation_id -> times the provider performed it
        self.status_script = list(status_script or [])
        self.before_return = before_return      # hook used to model a revoke arriving mid-fetch
        self.fetches = 0

    def fetch(self, consent_id, since=None):
        self.fetches += 1
        out = [dict(e) for e in self.events if since is None or e['posting_date'] >= since]
        if self.before_return:
            self.before_return()
        return out

    def submit(self, operation_id, kind):
        if self.submit_mode == 'reject':
            raise ProviderRejected('rejected')
        if self.submit_mode == 'timeout_before_apply':
            raise ProviderTimeout('timeout')
        self.applied.setdefault(operation_id, 0)
        if self.applied[operation_id] == 0:      # provider-side idempotency on operation id
            self.applied[operation_id] = 1
        if self.submit_mode == 'timeout_after_apply':
            raise ProviderTimeout('timeout')

    def status(self, operation_id):
        if self.status_script:
            return self.status_script.pop(0)
        return 'confirmed' if self.applied.get(operation_id) else 'failed'
