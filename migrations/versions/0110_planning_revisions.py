"""Immutable offline planning revisions.

Revision ID: 0110
Revises: 0101
"""
import sqlalchemy as sa
from alembic import op

revision = '0110'
down_revision = '0101'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('planning_revisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('operation_key', sa.String(64), nullable=False),
        sa.Column('request', sa.JSON(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'resource_id', 'revision', name='uq_planning_revision'),
        sa.UniqueConstraint('user_id', 'operation_key', name='uq_planning_operation'))
    op.create_index('ix_planning_revisions_user_id', 'planning_revisions', ['user_id'])
    if op.get_bind().dialect.name == 'sqlite':
        op.execute("CREATE TRIGGER planning_revisions_immutable BEFORE UPDATE ON planning_revisions "
                   "BEGIN SELECT RAISE(ABORT, 'immutable planning revision'); END")
    elif op.get_bind().dialect.name == 'postgresql':
        op.execute("CREATE FUNCTION planning_revisions_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'immutable planning revision'; END; $$")
        op.execute('CREATE TRIGGER planning_revisions_immutable BEFORE UPDATE ON planning_revisions '
                   'FOR EACH ROW EXECUTE FUNCTION planning_revisions_no_update()')
    else:
        raise RuntimeError('Unsupported planning database')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM planning_revisions')).scalar_one():
        raise RuntimeError('Planning evidence exists; preserve/export or authorized purge before downgrade')
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER planning_revisions_immutable ON planning_revisions')
        op.execute('DROP FUNCTION planning_revisions_no_update()')
    op.drop_index('ix_planning_revisions_user_id', table_name='planning_revisions')
    op.drop_table('planning_revisions')
