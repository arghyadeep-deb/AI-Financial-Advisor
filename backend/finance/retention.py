"""Explicit operator sweep for expired synthetic sources and aged orphan objects.

Never deletes source metadata, ledger evidence or active/unexpired objects.
Run after stopping uploads; an orphan must be older than the configured grace.
"""
from datetime import datetime, timezone
from uuid import UUID
from backend.models.models import StatementDocument, utcnow
from backend.finance.storage import configured_storage


def sweep(db, grace_seconds=86400, *, include_orphans=True, journal=None):
    if grace_seconds < 3600:
        raise ValueError('Orphan grace must be at least one hour')
    storage = configured_storage()
    documents = db.query(StatementDocument).all()
    from backend.models.models import PrivacyRequest
    held = journal.held_owners() if journal else set()
    retained = {(d.user_id, d.storage_key) for d in documents if d.expires_at > utcnow() or d.user_id in held}
    retained.update((r.user_id, r.storage_key) for r in db.query(PrivacyRequest) if r.expires_at > utcnow())
    expired = 0
    for document in documents:
        if document.expires_at <= utcnow() and document.user_id not in held:
            storage.delete(document.user_id, document.storage_key)
            expired += 1
    orphans = 0
    if include_orphans and storage.root.exists():
        for directory in storage.root.iterdir():
            if directory.is_symlink() or not directory.is_dir() or not directory.name.isdigit():
                continue
            owner = int(directory.name)
            if owner in held:
                continue
            for path in directory.iterdir():
                if path.is_symlink() or not path.is_file() or (owner, path.name) in retained:
                    continue
                try:
                    UUID(path.name.removesuffix('.tmp'))
                except ValueError:
                    continue
                age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
                if age > grace_seconds:
                    path.unlink()
                    orphans += 1
    return {'expired_sources': expired, 'orphan_objects': orphans}
