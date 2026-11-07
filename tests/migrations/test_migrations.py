"""T103 / T115 — migration coverage on clean and representative legacy databases."""
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from backend.core.migrations_runner import current_state, migrate, row_counts

NEW_TABLES = {"auth_sessions", "password_reset_tokens", "login_throttle",
              "profile_revisions", "analyses"}


def _url(p: Path) -> str:
    return f"sqlite:///{p.as_posix()}"


def _legacy_db(path: Path, versioned: bool):
    """Create a database shaped like 818b219 and fill it with synthetic rows."""
    url = _url(path)
    migrate(url, target="0001")
    con = sqlite3.connect(path)
    cur = con.cursor()
    for uid, email, name, h in [(1, "a@example.com", "Alice A", "ab" * 32),
                                (2, "b@example.com", "Bob B", "cd" * 32),
                                (3, "c@example.com", "Cara C", "ef" * 32)]:
        cur.execute("INSERT INTO users (id,email,full_name,hashed_password,is_active) VALUES (?,?,?,?,1)",
                    (uid, email, name, h))
    rows = [
        # user, income, expenses, savings, invest, debts, credit
        (1, 45000.10, 55000.0, 1234.56, 0.0, 0.0, 700),     # default score -> unknown
        (2, 65000.0, 40000.0, 10.0, 500000.0, 250000.5, 742),
        (3, float("inf"), 1e30, 5.0, 0.0, 0.0, None),      # corrupted values -> unknown, not guessed
    ]
    for uid, inc, exp, sav, inv, debt, cs in rows:
        cur.execute(
            "INSERT INTO financial_profiles (user_id,age,monthly_income,monthly_expenses,existing_savings,"
            "existing_investments,existing_debts,risk_tolerance,investment_horizon,employment_type,"
            "credit_score,monthly_credit_spend) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (uid, 30, inc, exp, sav, inv, debt, "moderate", "long", "salaried", cs, 0.0))
    cur.execute("INSERT INTO financial_state (user_id,health_score,portfolio_value,monthly_savings_rate) "
                "VALUES (2,70,7788940.0,38.5)")
    cur.execute("INSERT INTO threads (id,user_id,title,thread_type) VALUES (1,1,'t','general')")
    cur.execute("INSERT INTO messages (thread_id,user_id,role,content) VALUES (1,1,'user','hi')")
    cur.execute("INSERT INTO messages (thread_id,user_id,role,content) VALUES (1,1,'user','hi')")
    con.commit()
    if not versioned:
        cur.execute("DROP TABLE alembic_version")
        con.commit()
    con.close()
    return url


def test_fresh_database_reaches_head_with_all_tables(tmp_path):
    url = _url(tmp_path / "fresh.db")
    report = migrate(url)
    assert report["after"]["at_head"] is True
    names = set(inspect(create_engine(url)).get_table_names())
    assert NEW_TABLES <= names and {"users", "financial_profiles", "messages"} <= names


def test_upgrade_is_idempotent_at_head(tmp_path):
    url = _url(tmp_path / "x.db")
    migrate(url)
    again = migrate(url)
    assert again["after"]["at_head"] is True


@pytest.mark.parametrize("versioned", [True, False])
def test_legacy_database_is_migrated_without_losing_rows(tmp_path, versioned):
    path = tmp_path / "advisor.db"
    url = _legacy_db(path, versioned)
    before = row_counts(url)
    assert current_state(url)["status"] == ("behind" if versioned else "legacy_unversioned")

    report = migrate(url, backup_dir=tmp_path / "bk")
    assert report["after"]["at_head"] is True
    assert row_counts(url) == before
    if not versioned:
        assert report["backup"] and Path(report["backup"]).exists()

    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    prof = {r["user_id"]: r for r in con.execute("SELECT * FROM financial_profiles")}
    # exact paise from float, no binary error
    assert prof[1]["monthly_income_paise"] == 4500010
    assert prof[1]["monthly_expenses_paise"] == 5500000
    assert prof[1]["existing_savings_paise"] == 123456
    assert prof[2]["existing_debts_paise"] == 25000050
    # legacy float columns are untouched (rollback compatibility)
    assert prof[1]["monthly_income"] == 45000.10
    # corrupted legacy values are unknown (NULL), never guessed
    assert prof[3]["monthly_income_paise"] is None
    assert prof[3]["monthly_expenses_paise"] is None
    # inferred default credit score cleared; real-looking one flagged unverified
    assert prof[1]["credit_score"] is None and prof[1]["credit_score_source"] is None
    assert prof[2]["credit_score"] == 742 and prof[2]["credit_score_source"] == "legacy_unverified"
    # debt payment is a distinct, undeclared input
    assert prof[2]["monthly_debt_payment_paise"] is None
    # revision boundary
    assert {r["revision"] for r in prof.values()} == {1}
    revs = con.execute("SELECT user_id, revision, source FROM profile_revisions ORDER BY user_id").fetchall()
    assert [tuple(r) for r in revs] == [(1, 1, "migration"), (2, 1, "migration"), (3, 1, "migration")]
    # projected value never presented as observed holdings
    st = con.execute("SELECT portfolio_value, legacy_projected_value FROM financial_state WHERE user_id=2").fetchone()
    assert st[0] == 0 and st[1] == 7788940.0
    # legacy password hashes retained but marked for rehash
    users = con.execute("SELECT password_scheme, hashed_password FROM users ORDER BY id").fetchall()
    assert {u[0] for u in users} == {"legacy_hmac_sha256"}
    assert users[0][1] == "ab" * 32
    con.close()


def test_downgrade_restores_legacy_projected_value_and_legacy_code_shape(tmp_path):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    path = tmp_path / "advisor.db"
    url = _legacy_db(path, True)
    migrate(url)
    command.downgrade(_alembic_cfg(url), "0001")
    con = sqlite3.connect(path)
    assert con.execute("SELECT portfolio_value FROM financial_state WHERE user_id=2").fetchone()[0] == 7788940.0
    cols = {r[1] for r in con.execute("PRAGMA table_info(financial_profiles)")}
    assert "monthly_income_paise" not in cols and "monthly_income" in cols
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
    con.close()
    assert migrate(url)["after"]["at_head"] is True   # forward recovery after rollback


def test_message_client_id_unique_per_thread_and_role(tmp_path):
    url = _url(tmp_path / "m.db")
    migrate(url)
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO users (id,email,full_name,hashed_password,password_scheme) "
                       "VALUES (1,'a@e.com','A A','x','argon2id')"))
        c.execute(text("INSERT INTO threads (id,user_id,title,thread_type) VALUES (1,1,'t','g')"))
        c.execute(text("INSERT INTO messages (thread_id,user_id,role,content,client_message_id) "
                       "VALUES (1,1,'user','a','k1')"))
        c.execute(text("INSERT INTO messages (thread_id,user_id,role,content,client_message_id) "
                       "VALUES (1,1,'assistant','b','k1')"))
    with pytest.raises(Exception):
        with eng.begin() as c:
            c.execute(text("INSERT INTO messages (thread_id,user_id,role,content,client_message_id) "
                           "VALUES (1,1,'user','dup','k1')"))
