"""Offline SQLite restore drill helpers. Synthetic data only; no deployment.

Refuse overwrite and never restore over a live database. Production encrypted
backups and managed-key recovery are deliberately not represented by this helper.
"""
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.services.privacy.lifecycle import resume_delete

def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or destination.exists() or source == destination:
        raise ValueError('Existing source and unused destination required')
    # Exclusive creation prevents races from overwriting a different file.
    destination.touch(exist_ok=False)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Backup integrity failure')

def restore(source, destination, journal):
    if Path(destination).resolve() == journal.path:
        raise ValueError('Journal must be outside restore set')
    backup(source, destination)
    engine = create_engine('sqlite:///' + Path(destination).resolve().as_posix())
    try:
        with Session(engine) as db:
            journal.replay(db)
            for owner in journal.owners():
                resume_delete(db, owner, journal)
    finally:
        engine.dispose()
