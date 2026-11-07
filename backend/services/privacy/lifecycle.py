"""Lifecycle contracts for isolated synthetic drills.

Journal must live outside ALL restored backup sets. A caller must persist the
suppression before mutating the business DB, and replay it before reopening access.
No production endpoint is enabled until journal durability/retention is approved.
"""
import json
import sqlite3
from pathlib import Path
from backend.core.owned_stores import _registry, validate_coverage
from backend.models.models import User
from backend.services.auth_service import AuthService

class SuppressionJournal:
    def __init__(self, path):
        self.path = Path(path).resolve()
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS suppression (user_id INTEGER PRIMARY KEY)')

    def suppress(self, owner):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR IGNORE INTO suppression VALUES (?)', (owner,))

    def owners(self):
        with sqlite3.connect(self.path) as db:
            return [r[0] for r in db.execute('SELECT user_id FROM suppression')]

    def replay(self, db):
        for owner in self.owners():
            user = db.get(User, owner)
            if user:
                user.is_active = False
                AuthService(db).revoke_user_sessions(owner, 'deletion_suppression')
        db.commit()

def export_owned(db, user, password):
    AuthService(db).reauthenticate(user, password)
    validate_coverage()
    # Immediate authenticated response contract: never stored as a public file/link.
    return {'format_version': 1, 'account': {'id': user.id, 'email': user.email, 'full_name': user.full_name},
            'stores': {name: store.export(db, user.id) for name, store in _registry.items()}}

def delete_owned(db, user, password, journal):
    AuthService(db).reauthenticate(user, password)
    validate_coverage()
    journal.suppress(user.id)  # survives any subsequent failure or restore
    user.is_active = False
    AuthService(db).revoke_user_sessions(user.id, 'deletion')
    db.commit()  # immediately block access even if purge fails
    try:
        for store in _registry.values():
            store.purge(db, user.id)
        user.email = 'deleted-' + str(user.id) + '@invalid.example'
        user.full_name = 'Deleted account'
        user.hashed_password = '!deleted'
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'status': 'live_complete', 'backup_status': 'expiry_unapproved'}

def resume_delete(db, owner, journal):
    if owner not in journal.owners():
        raise ValueError('Suppression required')
    validate_coverage()
    user = db.get(User, owner)
    if not user:
        return
    user.is_active = False
    for store in _registry.values():
        store.purge(db, owner)
    user.email = 'deleted-' + str(owner) + '@invalid.example'
    user.full_name = 'Deleted account'
    user.hashed_password = '!deleted'
    db.commit()
