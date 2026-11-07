"""Explicit offline worker CLI. Run with synthetic storage and keys configured."""
from backend.workers import queue
from agents.monthly_finance_graph import run_claimed


def run_once(db, *, scanner_available=True):
    from backend.core.operations import heartbeat
    heartbeat(db, 'statements')
    db.commit()
    claimed = queue.claim(db, kind='statement')
    if claimed is None:
        return False
    run_claimed(db, *claimed, scanner_available=scanner_available)
    return True


if __name__ == '__main__':
    from backend.core.database import SessionLocal
    with SessionLocal() as db:
        run_once(db)
