"""Run one delivery from the shared outbox. No implicit live configuration."""
from backend.services.mail_service import run_once

if __name__ == '__main__':
    from backend.core.database import SessionLocal
    with SessionLocal() as db:
        run_once(db)
