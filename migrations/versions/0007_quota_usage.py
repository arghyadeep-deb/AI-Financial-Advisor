"""Quota counters. Revision 0007; parent 0006."""
import sqlalchemy as sa
from alembic import op
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("quota_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resource", sa.String(40), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("used", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "resource", "period", name="uq_quota_bucket"))

def downgrade():
    op.drop_table("quota_usage")
