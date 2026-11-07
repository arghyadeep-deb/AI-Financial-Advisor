"""Immutable synthetic allocation evidence.

Revision ID: 0050
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("allocation_plans",
                    sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("profile_revision", sa.Integer(), nullable=False),
                    sa.Column("suitability_revision", sa.Integer(), nullable=False),
                    sa.Column("input_snapshot", sa.JSON(), nullable=False),
                    sa.Column("result", sa.JSON(), nullable=False),
                    sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_allocation_plans_user_id", "allocation_plans", ["user_id"])
    if op.get_bind().dialect.name == "sqlite":
        op.execute("CREATE TRIGGER allocation_plans_immutable BEFORE UPDATE ON allocation_plans "
                   "BEGIN SELECT RAISE(ABORT, 'allocation plan is immutable'); END")
    elif op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE FUNCTION allocation_plans_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'allocation plan is immutable'; END; $$")
        op.execute("CREATE TRIGGER allocation_plans_immutable BEFORE UPDATE ON allocation_plans "
                   "FOR EACH ROW EXECUTE FUNCTION allocation_plans_no_update()")
    else:
        raise RuntimeError("unsupported allocation database")


def downgrade() -> None:
    # Never silently erase customer evidence on schema rollback. Operator must
    # export/restore or perform authorized privacy deletion before retrying.
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM allocation_plans")).scalar_one():
        raise RuntimeError("allocation evidence exists; preserve/export before downgrade")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER allocation_plans_immutable ON allocation_plans")
        op.execute("DROP FUNCTION allocation_plans_no_update()")
    op.drop_index("ix_allocation_plans_user_id", table_name="allocation_plans")
    op.drop_table("allocation_plans")
