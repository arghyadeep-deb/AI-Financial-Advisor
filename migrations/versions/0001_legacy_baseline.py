"""Legacy baseline schema (as created by Base.metadata.create_all at 818b219).

Fresh databases run this to reach the historical shape; existing databases
that already have these tables (e.g. advisor.db) are *stamped* at this
revision by backend.core.migrations_runner after a backup, never re-created.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "financial_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True),
        sa.Column("age", sa.Integer()),
        sa.Column("monthly_income", sa.Float()),
        sa.Column("monthly_expenses", sa.Float()),
        sa.Column("existing_savings", sa.Float()),
        sa.Column("existing_investments", sa.Float()),
        sa.Column("existing_debts", sa.Float()),
        sa.Column("risk_tolerance", sa.String()),
        sa.Column("investment_horizon", sa.String()),
        sa.Column("financial_goals", sa.JSON()),
        sa.Column("employment_type", sa.String()),
        sa.Column("credit_score", sa.Integer()),
        sa.Column("monthly_credit_spend", sa.Float()),
        sa.Column("top_spend_categories", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_financial_profiles_id", "financial_profiles", ["id"])

    op.create_table(
        "financial_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True),
        sa.Column("health_score", sa.Float()),
        sa.Column("portfolio_value", sa.Float()),
        sa.Column("monthly_savings_rate", sa.Float()),
        sa.Column("last_recommendations", sa.JSON()),
        sa.Column("last_updated", sa.DateTime()),
    )
    op.create_index("ix_financial_state_id", "financial_state", ["id"])

    op.create_table(
        "threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("user_name", sa.String()),
        sa.Column("user_email", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("thread_type", sa.String()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_threads_id", "threads", ["id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("threads.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("user_name", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("content", sa.Text()),
        sa.Column("extra_data", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_messages_id", "messages", ["id"])


def downgrade() -> None:
    for table in ("messages", "threads", "financial_state", "financial_profiles", "users"):
        op.drop_table(table)
