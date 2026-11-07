"""Explicit operator sweep for expired synthetic sources and aged orphan objects.

Never deletes source metadata, ledger evidence or active/unexpired objects.
Run after stopping uploads; an orphan must be older than the configured grace.
"""
from datetime import datetime, timezone
from uuid import UUID
from backend.models.models import StatementDocument, utcnow
from backend.finance.storage import configured_storage


def sweep(db, grace_seconds=86400):
    if grace_seconds < 3600:
        raise ValueError('Orphan grace must be at least one hour')
    storage = configured_storage()
    documents = db.query(StatementDocument).all()
    retained = {(d.user_id, d.storage_key) for d in documents if d.expires_at > utcnow()}
    expired = 0
    for document in documents:
        if document.expires_at <= utcnow():
            storage.delete(document.user_id, document.storage_key)
            expired += 1
    orphans = 0
    if storage.root.exists():
        for directory in storage.root.iterdir():
            if directory.is_symlink() or not directory.is_dir() or not directory.name.isdigit():
                continue
            owner = int(directory.name)
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
