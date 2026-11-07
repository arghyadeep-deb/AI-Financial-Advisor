"""Suppression journal v3, deliberately outside business Alembic/backup sets.

Run under BEGIN IMMEDIATE on the journal connection. This is an additive schema
migration with old JSON evidence preserved. Never open a business DB here.
"""
import json
import re


def upgrade_receipt_lookup(db):
    columns = {row[1] for row in db.execute('PRAGMA table_info(deletion_events)')}
    if 'receipt_digest' not in columns:
        db.execute('ALTER TABLE deletion_events ADD COLUMN receipt_digest TEXT')
        rows = db.execute("SELECT id,metadata_json FROM deletion_events WHERE state='receipt'")
        for identity, raw in rows:
            try:
                digest = json.loads(raw)['digest']
            except (ValueError, TypeError, KeyError):
                continue  # malformed legacy receipt never authorizes access
            if isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest):
                db.execute('UPDATE deletion_events SET receipt_digest=? WHERE id=?', (digest, identity))
    db.execute('CREATE INDEX IF NOT EXISTS ix_deletion_receipt_digest ON deletion_events(receipt_digest)')
    db.execute('CREATE INDEX IF NOT EXISTS ix_deletion_owner_state ON deletion_events(user_id,state,id)')


def downgrade_receipt_lookup(db):
    """Offline/quiesced only. Original JSON digests remain usable by old code."""
    db.execute('DROP INDEX IF EXISTS ix_deletion_receipt_digest')
    db.execute('DROP INDEX IF EXISTS ix_deletion_owner_state')
    if 'receipt_digest' in {row[1] for row in db.execute('PRAGMA table_info(deletion_events)')}:
        db.execute('ALTER TABLE deletion_events DROP COLUMN receipt_digest')
