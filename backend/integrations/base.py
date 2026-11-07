"""Provider-neutral bank adapter contract. No real provider exists; only the test-only fake implements it."""
from typing import Protocol


class ProviderTimeout(RuntimeError):
    """The request may or may not have reached the provider: outcome unknown."""


class ProviderRejected(RuntimeError):
    """The provider definitely did not perform the action."""


class BankAdapter(Protocol):
    name: str

    def fetch(self, consent_id: str, since: str | None) -> list[dict]:
        """Return [{'event_id', 'posting_date' (ISO), 'description', 'amount_paise' (signed int)}]. May repeat or reorder."""

    def submit(self, operation_id: str, kind: str) -> None:
        """Perform an external action keyed by operation_id (the provider must treat it idempotently)."""

    def status(self, operation_id: str) -> str:
        """'confirmed' | 'failed' | 'pending' | 'unknown'."""
