"""Lifecycle contracts for isolated synthetic drills.

Journal must live outside ALL restored backup sets. A caller must persist the
suppression before mutating the business DB, and replay it before reopening access.
No production endpoint is enabled until journal durability/retention is approved.
"""
import json
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from backend.core.owned_stores import _registry, validate_coverage
from backend.models.models import User
from backend.models.models import utcnow
from backend.services.auth_service import AuthService

class SuppressionJournal:
    def __init__(self, path):
        self.path = Path(path).resolve()
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS suppression (user_id INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS deletion_events '
                       '(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, state TEXT NOT NULL, '
                       'created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            # In-place, additive journal v2 upgrade; this journal is deliberately
            # outside the Alembic business database and every restore set.
            if 'metadata_json' not in {r[1] for r in db.execute('PRAGMA table_info(deletion_events)')}:
                db.execute('ALTER TABLE deletion_events ADD COLUMN metadata_json TEXT')

    def suppress(self, owner):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR IGNORE INTO suppression VALUES (?)', (owner,))

    def event(self, owner, state, metadata=None):
        if state not in {'requested', 'access_blocked', 'purging', 'live_complete', 'failed_retryable', 'held', 'legal_hold', 'hold_released', 'receipt'}:
            raise ValueError('Unsupported deletion state')
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO deletion_events(user_id,state,metadata_json) VALUES (?,?,?)',
                       (owner, state, json.dumps(metadata) if metadata else None))

    def place_hold(self, owner, basis, expires_at, scope):
        """Restricted operator contract, no public hold-creation endpoint.

        Safest initial scope is the whole account; no indefinite or free-text
        basis. Legal approval and operator IAM remain release prerequisites.
        """
        if type(owner) is not int or owner <= 0 or basis not in {'court_order', 'statutory_preservation'} or scope != 'account':
            raise ValueError('Explicit bounded legal basis and account scope required')
        if expires_at.tzinfo is not None or not utcnow() < expires_at <= utcnow() + timedelta(days=90):
            raise ValueError('Hold must expire within 90 days (UTC naive)')
        identity = secrets.token_hex(16)
        self.event(owner, 'legal_hold', {'id': identity, 'basis': basis, 'scope': scope, 'expires_at': expires_at.isoformat()})
        return identity

    def release_hold(self, owner, identity):
        self.event(owner, 'hold_released', {'id': identity})

    def held_owners(self):
        with sqlite3.connect(self.path) as db:
            records = db.execute("SELECT user_id,state,metadata_json FROM deletion_events WHERE state IN ('legal_hold','hold_released') ORDER BY id").fetchall()
        holds = {}
        for owner, state, raw in records:
            item = json.loads(raw)
            if state == 'legal_hold':
                holds[(owner, item['id'])] = datetime.fromisoformat(item['expires_at'])
            else:
                holds.pop((owner, item['id']), None)
        return {owner for (owner, _), expiry in holds.items() if expiry > utcnow()}

    def issue_receipt(self, owner):
        token = secrets.token_urlsafe(32)
        self.event(owner, 'receipt', {'digest': hashlib.sha256(token.encode()).hexdigest()})
        return token

    def receipt(self, token):
        from fastapi import HTTPException
        digest = hashlib.sha256(token.encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT user_id,metadata_json FROM deletion_events WHERE state='receipt'").fetchall()
            owner = next((owner for owner, raw in rows if secrets.compare_digest(json.loads(raw)['digest'], digest)), None)
            if owner is None:
                raise HTTPException(404, 'Resource not found.')
            row = db.execute("SELECT state,created_at FROM deletion_events WHERE user_id=? AND state IN ('access_blocked','purging','live_complete','failed_retryable','held') ORDER BY id DESC LIMIT 1", (owner,)).fetchone()
        return {'status': row[0] if row else 'access_blocked', 'updated_at': row[1] if row else None,
                'backup_status': 'expiry_unapproved'}

    def deletion_lag_seconds(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT user_id,state,created_at FROM deletion_events ORDER BY id").fetchall()
        latest, starts = {}, {}
        for owner, state, timestamp in rows:
            if state in {'requested', 'access_blocked', 'purging', 'failed_retryable', 'held', 'live_complete'}:
                latest[owner] = state
                starts.setdefault(owner, datetime.fromisoformat(timestamp))
        suppressed = set(self.owners())
        return max([0] + [int((utcnow() - starts[o]).total_seconds()) for o, state in latest.items() if state != 'live_complete' and o in suppressed])

    def pending_owners(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT user_id,state FROM deletion_events WHERE state IN ('access_blocked','purging','failed_retryable','held','live_complete') ORDER BY id").fetchall()
        latest = dict(rows)
        return [owner for owner in self.owners() if latest.get(owner) != 'live_complete']

    def owners(self):
        with sqlite3.connect(self.path) as db:
            return [r[0] for r in db.execute('SELECT user_id FROM suppression')]

    def contains(self, owner):
        with sqlite3.connect(self.path) as db:
            return db.execute('SELECT 1 FROM suppression WHERE user_id=?', (owner,)).fetchone() is not None

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
    if db.get_bind().dialect.name == 'sqlite' and journal.path == Path(db.get_bind().url.database).resolve():
        raise ValueError('Suppression journal must be separate from the business database')
    AuthService(db).reauthenticate(user, password)
    validate_coverage()
    journal.event(user.id, 'requested')
    journal.suppress(user.id)  # survives any subsequent failure or restore
    user.is_active = False
    AuthService(db).revoke_user_sessions(user.id, 'deletion')
    db.commit()  # immediately block access even if purge fails
    journal.event(user.id, 'access_blocked')
    receipt = journal.issue_receipt(user.id)
    if user.id in journal.held_owners():
        journal.event(user.id, 'held')
        return {'status': 'held', 'backup_status': 'expiry_unapproved', 'receipt_token': receipt}
    try:
        journal.event(user.id, 'purging')
        for store in _registry.values():
            store.purge(db, user.id)
        user.email = 'deleted-' + str(user.id) + '@invalid.example'
        user.full_name = 'Deleted account'
        user.hashed_password = '!deleted'
        db.commit()
        journal.event(user.id, 'live_complete')
    except Exception:
        db.rollback()
        journal.event(user.id, 'failed_retryable')
        raise
    return {'status': 'live_complete', 'backup_status': 'expiry_unapproved', 'receipt_token': receipt}

def resume_delete(db, owner, journal):
    if owner not in journal.owners():
        raise ValueError('Suppression required')
    validate_coverage()
    user = db.get(User, owner)
    if not user:
        journal.event(owner, 'live_complete')
        return
    user.is_active = False
    if owner in journal.held_owners():
        AuthService(db).revoke_user_sessions(owner, 'deletion_hold')
        db.commit()
        journal.event(owner, 'held')
        return
    try:
        journal.event(owner, 'purging')
        for store in _registry.values():
            store.purge(db, owner)
        user.email = 'deleted-' + str(owner) + '@invalid.example'
        user.full_name = 'Deleted account'
        user.hashed_password = '!deleted'
        db.commit()
        journal.event(owner, 'live_complete')
    except Exception:
        db.rollback()
        journal.event(owner, 'failed_retryable')
        raise


def configured_journal():
    from backend.core.config import config
    from fastapi import HTTPException
    if not config.SUPPRESSION_JOURNAL:
        raise HTTPException(503, 'Deletion unavailable: separate suppression journal is not configured.')
    return SuppressionJournal(config.SUPPRESSION_JOURNAL)
