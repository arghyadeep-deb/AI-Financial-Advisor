"""Private immutable household observation books. Revision 0170; parent 0141."""
import sqlalchemy as sa
from alembic import op

revision = '0170'
down_revision = '0141'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('household_revisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('operation_key', sa.String(64), nullable=False),
        sa.Column('request', sa.JSON(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'kind', 'revision', name='uq_household_revision'),
        sa.UniqueConstraint('user_id', 'operation_key', name='uq_household_operation'))
    op.create_index('ix_household_revisions_user_id', 'household_revisions', ['user_id'])
    if op.get_bind().dialect.name == 'sqlite':
        op.execute("CREATE TRIGGER household_revisions_immutable BEFORE UPDATE ON household_revisions "
                   "BEGIN SELECT RAISE(ABORT, 'immutable household revision'); END")
    elif op.get_bind().dialect.name == 'postgresql':
        op.execute("CREATE FUNCTION household_revisions_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'immutable household revision'; END; $$")
        op.execute('CREATE TRIGGER household_revisions_immutable BEFORE UPDATE ON household_revisions '
                   'FOR EACH ROW EXECUTE FUNCTION household_revisions_no_update()')
    else:
        raise RuntimeError('Unsupported household database')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM household_revisions')).scalar_one():
        raise RuntimeError('Household evidence exists; preserve/export or authorized purge before downgrade')
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER household_revisions_immutable ON household_revisions')
        op.execute('DROP FUNCTION household_revisions_no_update()')
    op.drop_index('ix_household_revisions_user_id', table_name='household_revisions')
    op.drop_table('household_revisions')
