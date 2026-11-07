"""Optional encrypted TOTP, one-use challenges and hashed recovery codes.

Revision ID: 0181
Revises: 0180
"""
from alembic import op
import sqlalchemy as sa

revision = '0181'
down_revision = '0180'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_sessions', sa.Column('mfa_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table('mfa_credentials',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('encrypted_secret', sa.Text(), nullable=False),
        sa.Column('generation', sa.String(36), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_step', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    for name in ('mfa_challenges', 'mfa_recovery_codes'):
        columns = [sa.Column('token_hash', sa.String(64), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('used_at', sa.DateTime(), nullable=True)]
        if name == 'mfa_challenges':
            columns.extend([sa.Column('generation', sa.String(36), nullable=False),
                sa.Column('expires_at', sa.DateTime(), nullable=False)])
        op.create_table(name, *columns)
        op.create_index('ix_' + name + '_user_id', name, ['user_id'])


def downgrade():
    for name in ('mfa_recovery_codes', 'mfa_challenges', 'mfa_credentials'):
        op.drop_table(name)
    op.drop_column('auth_sessions', 'mfa_verified')
