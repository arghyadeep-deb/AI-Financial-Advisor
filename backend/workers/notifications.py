"""One shared-queue scheduling tick; external channels remain disabled."""
from backend.workers import queue
from backend.services.notification_service import run_scheduled


def run_once(db):
    from backend.core.operations import heartbeat
    heartbeat(db, 'notifications')
    db.commit()
    claimed = queue.claim(db, kind='notification')
    if claimed is None:
        return False
    run_scheduled(db, *claimed)
    return True


if __name__ == '__main__':
    from backend.core.database import SessionLocal
    with SessionLocal() as db:
        run_once(db)
