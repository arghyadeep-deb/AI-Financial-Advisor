"""Explicit expiring membership and per-view read grants. Revision 0171."""
import sqlalchemy as sa
from alembic import op

revision = '0171'
down_revision = '0170'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('households',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('label', sa.String(80), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False))
    op.create_index('ix_households_user_id', 'households', ['user_id'])
    op.create_table('household_memberships',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('household_id', sa.String(36), sa.ForeignKey('households.id'), nullable=False),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.UniqueConstraint('household_id', 'member_id', name='uq_household_member'))
    op.create_index('ix_household_memberships_user_id', 'household_memberships', ['user_id'])
    op.create_table('household_grants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('household_id', sa.String(36), sa.ForeignKey('households.id'), nullable=False),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('view', sa.String(24), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('household_id', 'user_id', 'member_id', 'view', name='uq_household_grant'))
    op.create_index('ix_household_grants_user_id', 'household_grants', ['user_id'])


def downgrade():
    for table in ('household_grants', 'household_memberships', 'households'):
        if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM ' + table)).scalar_one():
            raise RuntimeError('Household sharing evidence exists; preserve/export or authorized purge before downgrade')
    for table in ('household_grants', 'household_memberships', 'households'):
        op.drop_index('ix_' + table + '_user_id', table_name=table)
        op.drop_table(table)
