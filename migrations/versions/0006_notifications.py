"""In-app delivery contracts. Revision 0006; parent 0005."""
import sqlalchemy as sa
from alembic import op
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("notification_preferences",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("quiet_start", sa.Integer()), sa.Column("quiet_end", sa.Integer()))
    op.create_table("delivery_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_key", sa.String(100), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "event_key", name="uq_delivery_owner_event"))
    op.create_index("ix_delivery_attempts_user_id", "delivery_attempts", ["user_id"])

def downgrade():
    op.drop_index("ix_delivery_attempts_user_id", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")
    op.drop_table("notification_preferences")
