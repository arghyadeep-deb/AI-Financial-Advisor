"""Shared pytest configuration.

Environment is pinned *before* any application module is imported so that
tests never read a developer's real .env values, never call model providers
and never export traces.  Every test run uses an isolated SQLite file in a
temporary directory (PostgreSQL integration tests are opt-in via
TEST_POSTGRES_URL and are skipped otherwise).
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="advisor-tests-")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'session.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-only-signing-key-0123456789abcdef0123456789abcdef"
os.environ["LEGACY_PASSWORD_SECRET"] = "legacy-test-secret"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""
for _i in range(1, 5):
    os.environ[f"GROQ_API_KEY_{_i}"] = ""
    os.environ[f"GOOGLE_API_KEY_{_i}"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
os.environ['MAIL_PROVIDER'] = 'fake'
os.environ['MAIL_LIVE_ENABLED'] = 'false'
os.environ['RESEND_API_KEY'] = ''
os.environ['NOTIFICATION_EMAIL_ENABLED'] = 'false'
os.environ['MFA_REQUIRED'] = 'false'

import pytest  # noqa: E402


@pytest.fixture()
def db_engine(tmp_path):
    """Fresh isolated database per test, built via the real Alembic migrations."""
    from backend.core import database

    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    eng = database.create_db_engine(url)
    database.upgrade_to_head(url)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(db_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from backend.core.database import get_db
    from backend.main import app

    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        c.session_factory = Session
        yield c
    app.dependency_overrides.clear()


PROFILE_DEFICIT = {
    "age": 30,
    "employment_type": "salaried",
    "monthly_income": 45000,
    "monthly_expenses": 55000,
    "existing_savings": 0,
    "existing_investments": 0,
    "existing_debts": 0,
    "risk_tolerance": "moderate",
    "investment_horizon": "long",
    "financial_goals": ["retirement"],
    "monthly_credit_spend": 0,
    "top_spend_categories": [],
}


@pytest.fixture()
def deficit_profile():
    return dict(PROFILE_DEFICIT)


@pytest.fixture(autouse=True)
def _no_inflight_wait(monkeypatch):
    """Duplicate-turn waiting is exercised explicitly; other tests must not sleep."""
    import backend.services.chat_service as cs
    monkeypatch.setattr(cs, "IN_FLIGHT_SECONDS", 0.0)
