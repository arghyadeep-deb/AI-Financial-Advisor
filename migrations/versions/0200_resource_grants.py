"""D06 resource grants; legacy whole-book grants remain inert."""
import sqlalchemy as sa
from alembic import op
revision = '0200'
down_revision = '0173'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('household_grants') as batch:
        batch.add_column(sa.Column('resource', sa.String(80), nullable=True))
        batch.add_column(sa.Column('permissions', sa.JSON(), nullable=False, server_default='[]'))
        batch.drop_constraint('uq_household_grant', type_='unique')
        batch.create_unique_constraint('uq_household_grant', ['household_id', 'user_id', 'member_id', 'view', 'resource'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM household_grants WHERE resource IS NOT NULL')).scalar_one():
        raise RuntimeError('Resource grants exist; export/purge before downgrade')
    with op.batch_alter_table('household_grants') as batch:
        batch.drop_constraint('uq_household_grant', type_='unique')
        batch.drop_column('permissions')
        batch.drop_column('resource')
        batch.create_unique_constraint('uq_household_grant', ['household_id', 'user_id', 'member_id', 'view'])
