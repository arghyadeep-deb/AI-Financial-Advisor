"""Private lifecycle export requests.

Revision ID: 0101
Revises: 0100
"""
import sqlalchemy as sa
from alembic import op

revision = '0101'
down_revision = '0100'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('privacy_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('state', sa.String(24), nullable=False),
        sa.Column('storage_key', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False))
    op.create_index('ix_privacy_requests_user_id', 'privacy_requests', ['user_id'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM privacy_requests')).scalar_one():
        raise RuntimeError('export delivery evidence exists; preserve/purge before downgrade')
    op.drop_index('ix_privacy_requests_user_id', table_name='privacy_requests')
    op.drop_table('privacy_requests')
