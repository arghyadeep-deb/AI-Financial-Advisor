"""One user message per (owner, client_message_id), across threads.

A retried FIRST chat message has no thread id yet, so the per-thread unique
constraint cannot stop two concurrent requests creating two threads.  This
partial unique index makes the owner + client id association atomic.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_WHERE = sa.text("role = 'user' AND client_message_id IS NOT NULL")


def upgrade() -> None:
    op.create_index("uq_messages_owner_client_id", "messages", ["user_id", "client_message_id"], unique=True,
                    sqlite_where=_WHERE, postgresql_where=_WHERE)


def downgrade() -> None:
    op.drop_index("uq_messages_owner_client_id", table_name="messages")
