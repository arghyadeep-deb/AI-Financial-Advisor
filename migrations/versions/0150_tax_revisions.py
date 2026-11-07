"""Immutable synthetic tax cases, reviews and drafts.

Revision ID: 0150
Revises: 0141
"""
import sqlalchemy as sa
from alembic import op

revision = '0150'
down_revision = '0141'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('tax_revisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('operation_key', sa.String(64), nullable=False),
        sa.Column('request', sa.JSON(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'case_id', 'kind', 'revision', name='uq_tax_revision'),
        sa.UniqueConstraint('user_id', 'operation_key', name='uq_tax_operation'))
    op.create_index('ix_tax_revisions_user_id', 'tax_revisions', ['user_id'])
    dialect = op.get_bind().dialect.name
    if dialect == 'sqlite':
        op.execute("CREATE TRIGGER tax_revisions_immutable BEFORE UPDATE ON tax_revisions "
                   "BEGIN SELECT RAISE(ABORT, 'immutable tax revision'); END")
    elif dialect == 'postgresql':
        op.execute("CREATE FUNCTION tax_revisions_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'immutable tax revision'; END; $$")
        op.execute('CREATE TRIGGER tax_revisions_immutable BEFORE UPDATE ON tax_revisions '
                   'FOR EACH ROW EXECUTE FUNCTION tax_revisions_no_update()')
    else:
        raise RuntimeError('Unsupported tax database')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM tax_revisions')).scalar_one():
        raise RuntimeError('Tax evidence exists; preserve/export or authorized purge before downgrade')
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER tax_revisions_immutable ON tax_revisions')
        op.execute('DROP FUNCTION tax_revisions_no_update()')
    op.drop_index('ix_tax_revisions_user_id', table_name='tax_revisions')
    op.drop_table('tax_revisions')
