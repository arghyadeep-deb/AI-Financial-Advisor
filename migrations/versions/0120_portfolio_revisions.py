"""Immutable confirmed portfolio and suitability revisions.

Revision ID: 0120
Revises: 0110
"""
import sqlalchemy as sa
from alembic import op

revision = '0120'
down_revision = '0110'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('portfolio_revisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('operation_key', sa.String(64), nullable=False),
        sa.Column('request', sa.JSON(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'kind', 'revision', name='uq_portfolio_revision'),
        sa.UniqueConstraint('user_id', 'operation_key', name='uq_portfolio_operation'))
    op.create_index('ix_portfolio_revisions_user_id', 'portfolio_revisions', ['user_id'])
    dialect = op.get_bind().dialect.name
    if dialect == 'sqlite':
        op.execute("CREATE TRIGGER portfolio_revisions_immutable BEFORE UPDATE ON portfolio_revisions "
                   "BEGIN SELECT RAISE(ABORT, 'immutable portfolio revision'); END")
    elif dialect == 'postgresql':
        op.execute("CREATE FUNCTION portfolio_revisions_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'immutable portfolio revision'; END; $$")
        op.execute('CREATE TRIGGER portfolio_revisions_immutable BEFORE UPDATE ON portfolio_revisions '
                   'FOR EACH ROW EXECUTE FUNCTION portfolio_revisions_no_update()')
    else:
        raise RuntimeError('Unsupported portfolio database')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM portfolio_revisions')).scalar_one():
        raise RuntimeError('Portfolio evidence exists; preserve/export or authorized purge before downgrade')
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER portfolio_revisions_immutable ON portfolio_revisions')
        op.execute('DROP FUNCTION portfolio_revisions_no_update()')
    op.drop_index('ix_portfolio_revisions_user_id', table_name='portfolio_revisions')
    op.drop_table('portfolio_revisions')
