"""Integration consent, event de-duplication and external operation state (test-only adapter)."""
import sqlalchemy as sa
from alembic import op
revision = '0230'
down_revision = '0220'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('integration_consents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('provider', sa.String(40), nullable=False),
        sa.Column('account_id', sa.String(36), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('state', sa.String(12), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.create_table('integration_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('provider', sa.String(40), nullable=False),
        sa.Column('event_id', sa.String(80), nullable=False),
        sa.Column('consent_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'provider', 'event_id', name='uq_integration_event'))
    op.create_table('integration_operations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('consent_id', sa.String(36), nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('idempotency_key', sa.String(64), nullable=False),
        sa.Column('state', sa.String(12), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'idempotency_key', name='uq_integration_operation_key'))


def downgrade():
    bind = op.get_bind()
    for table in ('integration_operations', 'integration_events', 'integration_consents'):
        if bind.execute(sa.text('SELECT COUNT(*) FROM ' + table)).scalar_one():
            raise RuntimeError('Integration records exist; export/purge before downgrade')
    for table in ('integration_operations', 'integration_events', 'integration_consents'):
        op.drop_table(table)
