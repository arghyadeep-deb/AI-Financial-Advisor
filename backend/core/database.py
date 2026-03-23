from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.models import Base
from backend.core.config import config


engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables ready ✓")


def get_db():
    """FastAPI dependency — yields DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()