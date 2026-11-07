"""One runnable operations tick. No daemon is implicitly installed.

Run `python -m backend.workers.operations` under a supervised minute timer.
Normal ticks never orphan-sweep; that requires uploads stopped and an explicit
--quiesced-orphans invocation. Journal is required even for retention: unknown
holds must never be treated as no holds. All output is aggregate metadata.
"""
from datetime import timedelta
from backend.core.config import config
from backend.core.operations import heartbeat, _row
from backend.models.models import OperationalCounter, utcnow
from backend.services.privacy.lifecycle import configured_journal, resume_delete


def run_once(db, journal, *, quiesced_orphans=False):
    from backend.finance.retention import sweep
    from backend.services.privacy.exports import expire
    from backend.workers.queue import sweep_exhausted
    # Serializes competing retention ticks; a failed tick rolls back its clock.
    row = _row(db, 'retention_sweep', 'current')
    from sqlalchemy import update
    now = utcnow()
    due = db.execute(update(OperationalCounter).where(OperationalCounter.key == 'retention_sweep',
        OperationalCounter.period == 'current',
        (OperationalCounter.used == 0) | (OperationalCounter.updated_at <= now - timedelta(seconds=config.RETENTION_INTERVAL_SECONDS))
        ).values(used=1, updated_at=now)).rowcount
    result = {'retention_ran': bool(due), 'deletions_resumed': 0}
    try:
        if due or quiesced_orphans:
            result.update(sweep(db, include_orphans=quiesced_orphans, journal=journal))
            result['expired_exports'] = expire(db, journal=journal)
        for owner in journal.pending_owners():
            if owner not in journal.held_owners():
                resume_delete(db, owner, journal)
                result['deletions_resumed'] += 1
        heartbeat(db, 'retention')
        db.query(OperationalCounter).filter(OperationalCounter.period < (now - timedelta(days=7)).date().isoformat(),
                                           OperationalCounter.period != 'current').delete(synchronize_session=False)
        db.commit()
        result['dead_letters'] = sweep_exhausted(db)
        return result
    except Exception:
        db.rollback()
        raise


def main():
    import argparse
    import json
    from backend.core.database import SessionLocal
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quiesced-orphans', action='store_true')
    args = parser.parse_args()
    config.validate()
    with SessionLocal() as db:
        print(json.dumps(run_once(db, configured_journal(), quiesced_orphans=args.quiesced_orphans)))


if __name__ == '__main__':
    main()
