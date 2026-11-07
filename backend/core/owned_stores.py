"""Ownership registry: future owners MUST register export and idempotent purge hooks.

No fallback exporter: unregistered tables fail coverage validation. Hooks participate
in the caller transaction and must never commit or send external requests.
"""
from dataclasses import dataclass
from typing import Callable
from sqlalchemy import inspect
from backend.models.models import Base

@dataclass(frozen=True)
class OwnedStore:
    name: str
    tables: frozenset[str]
    export: Callable
    purge: Callable
    purpose: str
    retention: str

_registry: dict[str, OwnedStore] = {}

def register_owned_store(store: OwnedStore):
    if store.name in _registry:
        raise ValueError("Store already registered")
    if not store.tables or not store.retention or not store.purpose:
        raise ValueError("Inventory metadata required")
    overlap = set().union(*(s.tables for s in _registry.values())) if _registry else set()
    if overlap & store.tables:
        raise ValueError("Table already owned")
    _registry[store.name] = store

def validate_coverage():
    covered = set().union(*(s.tables for s in _registry.values())) if _registry else set()
    missing = set(Base.metadata.tables) - covered - {"users", "login_throttle"}
    if missing:
        raise RuntimeError("Unregistered stores: " + ",".join(sorted(missing)))

def inventory():
    return [{"store": s.name, "tables": sorted(s.tables), "purpose": s.purpose,
             "retention": s.retention} for s in _registry.values()]

def register_database_store(name, models, purpose, before_purge=None):
    def export(db, owner):
        return {m.__tablename__: [{c.name: getattr(row, c.name) for c in inspect(m).columns
                if c.name not in {"token_hash"}} for row in db.query(m).filter(m.user_id == owner)] for m in models}
    def purge(db, owner):
        if before_purge:
            before_purge(db, owner)
        for model in models:
            db.query(model).filter(model.user_id == owner).delete(synchronize_session=False)
    register_owned_store(OwnedStore(name, frozenset(m.__tablename__ for m in models), export, purge,
                                   purpose, "synthetic-only; production retention pending D03"))

from backend.models.models import (AuthSession, PasswordResetToken, FinancialProfile,
    FinancialState, ProfileRevision, Analysis, Thread, Message, ConsentRecord)
register_database_store("identity", [AuthSession, PasswordResetToken], "account security")
register_database_store("finance", [Analysis, ProfileRevision, FinancialState, FinancialProfile], "deterministic advice")
register_database_store("chat", [Message, Thread], "conversation history")
register_database_store("consent", [ConsentRecord], "processing choices")
from backend.models.models import WorkItem, NotificationPreference, DeliveryAttempt
register_database_store("queue", [WorkItem], "bounded background work")
register_database_store("notifications", [DeliveryAttempt, NotificationPreference], "in-app notices")
from backend.models.models import QuotaUsage
register_database_store("quotas", [QuotaUsage], "resource accounting")
from backend.models.models import PlanningRevision
register_database_store('planning', [PlanningRevision], 'versioned offline budgets, obligations, goals and debt assumptions')
from backend.models.models import AllocationPlan
register_database_store("allocation", [AllocationPlan], "hypothetical allocation scenarios (feature 007, gated off)")
from backend.models.models import (StatementAccount, StatementDocument, StatementImport, StatementRow,
    LedgerEntry, LedgerEvidence, LedgerCorrection, LedgerLink, MonthlyReport)
_statement_models = [MonthlyReport, LedgerLink, LedgerCorrection, LedgerEvidence, LedgerEntry,
                     StatementRow, StatementImport, StatementDocument, StatementAccount]
def _purge_statement_sources(db, owner):
    documents = db.query(StatementDocument).filter_by(user_id=owner).all()
    if documents:
        from backend.finance.storage import configured_storage
        storage = configured_storage()  # unavailable keys/storage fail closed; deletion can resume
        for document in documents:
            storage.delete(owner, document.storage_key)
register_database_store("statements", _statement_models, "synthetic statement evidence and observed monthly facts",
                        before_purge=_purge_statement_sources)
from backend.models.models import PrivacyRequest


def _purge_export_files(db, owner):
    requests = db.query(PrivacyRequest).filter_by(user_id=owner).all()
    if requests:
        from backend.finance.storage import configured_storage
        storage = configured_storage()
        for request in requests:
            storage.delete(owner, request.storage_key)


register_database_store('privacy_requests', [PrivacyRequest], 'short-lived private export delivery',
                        before_purge=_purge_export_files)
