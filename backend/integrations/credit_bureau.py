"""Credit-data adapter interface (feature 005). No provider is selected; live integration is disabled.

Only the interface and a disabled implementation live here. A test-only fake lives under tests/. Any real adapter needs the
owner's provider choice, consent flow and legal review first.
"""
from typing import Protocol


class IntegrationDisabled(RuntimeError):
    pass


class CreditBureauAdapter(Protocol):
    def fetch_summary(self, consent_reference: str) -> dict: ...


class DisabledAdapter:
    status = 'disabled'
    reason = 'No provider is selected and live integrations are disabled. Enter a dated score manually.'

    def fetch_summary(self, consent_reference: str) -> dict:
        raise IntegrationDisabled(self.reason)


def get_adapter() -> CreditBureauAdapter:
    return DisabledAdapter()
