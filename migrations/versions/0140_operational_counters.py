"""Nonpersonal aggregate budgets and worker liveness.

Revision ID: 0140
Revises: 0110
"""
import sqlalchemy as sa
from alembic import op

revision = '0140'
down_revision = '0110'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('operational_counters',
        sa.Column('key', sa.String(40), primary_key=True),
        sa.Column('period', sa.String(10), primary_key=True),
        sa.Column('used', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False))


def downgrade():
    # Only aggregate admission counters and heartbeat timestamps; no user evidence.
    op.drop_table('operational_counters')
