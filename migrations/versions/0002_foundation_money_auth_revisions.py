"""Foundation: exact money, profile revisions, auth lifecycle, analysis records, chat idempotency.

Legacy behaviour (documented per architecture.md):
* Float money columns are KEPT (rollback compatibility) and every legacy row is
  backfilled into integer paise.  Values that are NaN/inf/negative/over the
  supported maximum are NOT guessed: the paise column stays NULL ("unknown")
  and the row is counted in the migration report.
* A legacy credit score of exactly 700 is the old inferred default and is
  cleared to NULL (unknown).  Other stored scores are kept and marked
  ``legacy_unverified``.
* ``financial_state.portfolio_value`` historically held a PROJECTED 10-year
  corpus.  The value is copied to ``legacy_projected_value`` and the observed
  column reset to 0 so a projection can never be promoted to a holding.
* Every user starts at profile revision 1 with a ``migration`` revision row.
* Password hashes stay as ``legacy_hmac_sha256`` until the owner next logs in
  (rehash to Argon2id) or resets the password.

Revision ID: 0002
Revises: 0001
"""
import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MAX_PAISE = 10 ** 13


def _to_paise(value):
    """Exact paise from a legacy float; None when it cannot be trusted."""
    if value is None:
        return None
    try:
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        dec = Decimal(repr(value)) if isinstance(value, float) else Decimal(str(value))
    except InvalidOperation:
        return None
    if not dec.is_finite() or dec < 0 or dec * 100 > MAX_PAISE:
        return None
    try:
        paise = int((dec * 100).quantize(Decimal(1)))
    except InvalidOperation:
        return None
    return paise if paise <= MAX_PAISE else None


def upgrade() -> None:
    bind = op.get_bind()

    # ── users ─────────────────────────────────────────────────────────────
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("password_scheme", sa.String(), nullable=False,
                               server_default="legacy_hmac_sha256"))
        b.add_column(sa.Column("password_changed_at", sa.DateTime(), nullable=True))

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(40), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "login_throttle",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )

    # ── financial_profiles ────────────────────────────────────────────────
    with op.batch_alter_table("financial_profiles") as b:
        b.add_column(sa.Column("credit_score_source", sa.String(24), nullable=True))
        for col in ("monthly_income_paise", "monthly_expenses_paise", "existing_savings_paise",
                    "existing_investments_paise", "existing_debts_paise",
                    "monthly_debt_payment_paise", "monthly_credit_spend_paise"):
            b.add_column(sa.Column(col, sa.BigInteger(), nullable=True))
        b.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("financial_state") as b:
        b.add_column(sa.Column("legacy_projected_value", sa.Float(), nullable=True))
        b.add_column(sa.Column("health_score_known", sa.Boolean(), nullable=True))
        b.add_column(sa.Column("health_score_revision", sa.Integer(), nullable=True))

    op.create_table(
        "profile_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(24), nullable=False, server_default="user_edit"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "revision", name="uq_profile_revision"),
    )
    op.create_index("ix_profile_revisions_user_id", "profile_revisions", ["user_id"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("profile_revision", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(24), nullable=False),
        sa.Column("is_scenario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("snapshot", sa.JSON()),
        sa.Column("results", sa.JSON()),
        sa.Column("errors", sa.JSON()),
        sa.Column("section_status", sa.JSON()),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.create_index("ix_analyses_user_kind_completed", "analyses", ["user_id", "kind", "completed_at"])

    # ── messages (idempotent chat turns) ──────────────────────────────────
    with op.batch_alter_table("messages") as b:
        b.add_column(sa.Column("client_message_id", sa.String(64), nullable=True))
        b.create_unique_constraint("uq_message_client_id", ["thread_id", "client_message_id", "role"])

    # ── Backfill ──────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    profiles = sa.table(
        "financial_profiles",
        sa.column("id"), sa.column("user_id"), sa.column("monthly_income"), sa.column("monthly_expenses"),
        sa.column("existing_savings"), sa.column("existing_investments"), sa.column("existing_debts"),
        sa.column("monthly_credit_spend"), sa.column("credit_score"), sa.column("credit_score_source"),
        sa.column("monthly_income_paise"), sa.column("monthly_expenses_paise"),
        sa.column("existing_savings_paise"), sa.column("existing_investments_paise"),
        sa.column("existing_debts_paise"), sa.column("monthly_credit_spend_paise"),
        sa.column("age"), sa.column("risk_tolerance"), sa.column("investment_horizon"),
        sa.column("employment_type"), sa.column("revision"),
    )
    revs = sa.table(
        "profile_revisions",
        sa.column("user_id"), sa.column("revision"), sa.column("snapshot", sa.JSON()),
        sa.column("source"), sa.column("created_at"),
    )
    rows = bind.execute(sa.select(profiles)).mappings().all()
    unknown_money = 0
    credit_cleared = 0
    for r in rows:
        vals = {
            "monthly_income_paise": _to_paise(r["monthly_income"]),
            "monthly_expenses_paise": _to_paise(r["monthly_expenses"]),
            "existing_savings_paise": _to_paise(r["existing_savings"] or 0),
            "existing_investments_paise": _to_paise(r["existing_investments"] or 0),
            "existing_debts_paise": _to_paise(r["existing_debts"] or 0),
            "monthly_credit_spend_paise": _to_paise(r["monthly_credit_spend"] or 0),
        }
        unknown_money += sum(1 for v in vals.values() if v is None)
        score = r["credit_score"]
        if score == 700:                       # old inferred default -> unknown
            vals["credit_score"] = None
            vals["credit_score_source"] = None
            credit_cleared += 1
        elif score is not None:
            vals["credit_score_source"] = "legacy_unverified"
        bind.execute(profiles.update().where(profiles.c.id == r["id"]).values(**vals))
        bind.execute(revs.insert().values(
            user_id=r["user_id"], revision=1, source="migration", created_at=now,
            snapshot={**{k: v for k, v in vals.items() if k.endswith("_paise")},
                      "age": r["age"], "risk_tolerance": r["risk_tolerance"],
                      "investment_horizon": r["investment_horizon"],
                      "employment_type": r["employment_type"],
                      "credit_score": vals.get("credit_score", score)},
        ))

    bind.execute(sa.text(
        "UPDATE financial_state SET legacy_projected_value = portfolio_value, portfolio_value = 0 "
        "WHERE portfolio_value IS NOT NULL AND portfolio_value <> 0"))
    print(f"[migration 0002] profiles={len(rows)} unknown_money_fields={unknown_money} "
          f"legacy_credit_default_cleared={credit_cleared}")


def downgrade() -> None:
    """Forward-recovery is preferred.  Downgrade drops only additive objects;
    legacy float columns were never modified so the 818b219 code keeps working.
    Dropped: sessions, reset tokens, throttle, revisions, analyses, paise columns.
    """
    op.get_bind().execute(sa.text(
        "UPDATE financial_state SET portfolio_value = legacy_projected_value "
        "WHERE legacy_projected_value IS NOT NULL"))
    with op.batch_alter_table("messages") as b:
        b.drop_constraint("uq_message_client_id", type_="unique")
        b.drop_column("client_message_id")
    op.drop_table("analyses")
    op.drop_table("profile_revisions")
    with op.batch_alter_table("financial_state") as b:
        b.drop_column("health_score_revision")
        b.drop_column("health_score_known")
        b.drop_column("legacy_projected_value")
    with op.batch_alter_table("financial_profiles") as b:
        for col in ("schema_version", "revision", "monthly_credit_spend_paise",
                    "monthly_debt_payment_paise", "existing_debts_paise",
                    "existing_investments_paise", "existing_savings_paise",
                    "monthly_expenses_paise", "monthly_income_paise", "credit_score_source"):
            b.drop_column(col)
    op.drop_table("login_throttle")
    op.drop_table("password_reset_tokens")
    op.drop_table("auth_sessions")
    with op.batch_alter_table("users") as b:
        b.drop_column("password_changed_at")
        b.drop_column("password_scheme")
