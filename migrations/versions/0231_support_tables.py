"""Support access grants and audit log."""
import sqlalchemy as sa
from alembic import op
revision = '0231'
down_revision = '0230'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('support_grants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_table('support_access_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('operator', sa.String(80), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('target', sa.String(80), nullable=False),
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('outcome', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))


def downgrade():
    bind = op.get_bind()
    for table in ('support_grants', 'support_access_log'):
        if bind.execute(sa.text('SELECT COUNT(*) FROM ' + table)).scalar_one():
            raise RuntimeError('Support records exist; export/purge before downgrade')
        op.drop_table(table)
