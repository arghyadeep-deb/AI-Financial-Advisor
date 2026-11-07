"""Consent choices. Revision 0004; parent 0003."""
import sqlalchemy as sa
from alembic import op
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("consent_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("notice_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])

def downgrade():
    # Operators must export choices before intentionally downgrading.
    op.drop_index("ix_consent_records_user_id", table_name="consent_records")
    op.drop_table("consent_records")
