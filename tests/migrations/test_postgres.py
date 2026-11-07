"""T103 — PostgreSQL parity.  Opt-in: set TEST_POSTGRES_URL to a throwaway database (it is dropped/recreated)."""
import os

import pytest
from sqlalchemy import create_engine, inspect, text

URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_POSTGRES_URL not set (PostgreSQL not available locally)")


def test_migrations_reach_head_and_unique_idempotency_constraint_exists():
    from backend.core.migrations_runner import current_state, migrate
    eng = create_engine(URL)
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    migrate(URL)
    assert current_state(URL)["at_head"] is True
    uniques = inspect(eng).get_unique_constraints("messages")
    assert any(set(u["column_names"]) == {"thread_id", "client_message_id", "role"} for u in uniques)


def test_profile_revision_compare_and_swap_is_atomic_under_concurrency():
    """Two writers race on the same expected revision: exactly one wins."""
    import threading
    from backend.core.migrations_runner import migrate
    from sqlalchemy.orm import sessionmaker
    from backend.models.models import User
    from fastapi import HTTPException
    from backend.services.profile_service import ProfileService
    from decimal import Decimal
    migrate(URL)
    eng = create_engine(URL)
    S = sessionmaker(bind=eng)
    with S() as db:
        u = User(email="race@example.com", full_name="Race", hashed_password="x", is_active=True)
        db.add(u)
        db.commit()
        uid = u.id
    base = {"age": 30, "employment_type": "salaried", "monthly_income": Decimal("50000"),
            "monthly_expenses": Decimal("20000"), "existing_savings": Decimal("0"),
            "existing_investments": Decimal("0"), "existing_debts": Decimal("0"),
            "monthly_credit_spend": Decimal("0"), "monthly_debt_payment": None, "credit_score": None,
            "risk_tolerance": "moderate", "investment_horizon": "long"}
    with S() as db:
        ProfileService(db).save(uid, base)
    results = []

    def writer(income):
        with S() as db:
            try:
                ProfileService(db).save(uid, {**base, "monthly_income": Decimal(income), "expected_revision": 1})
                results.append("ok")
            except HTTPException as exc:
                results.append("conflict" if exc.status_code == 409 else "error")

    ts = [threading.Thread(target=writer, args=(i,)) for i in ("51000", "52000")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["conflict", "ok"]
