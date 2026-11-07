"""Shared transactional outbox. Revision 0005; parent 0004."""
import sqlalchemy as sa
from alembic import op
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("work_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_key", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("consent_purpose", sa.String(40)),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("fence", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("lease_until", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "event_key", name="uq_work_owner_event"))
    op.create_index("ix_work_items_user_id", "work_items", ["user_id"])

def downgrade():
    op.drop_index("ix_work_items_user_id", table_name="work_items")
    op.drop_table("work_items")
