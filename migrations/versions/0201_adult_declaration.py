"""Unverified pilot self-declarations; no identity evidence."""
import sqlalchemy as sa
from alembic import op
revision = '0201'
down_revision = '0200'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('households', 'household_memberships'):
        op.add_column(table, sa.Column('adult_declared_at', sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column('adult_statement_version', sa.String(40), nullable=True))
        op.add_column(table, sa.Column('adult_assurance', sa.String(20), nullable=True))


def downgrade():
    for table in ('households', 'household_memberships'):
        if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM ' + table + ' WHERE adult_declared_at IS NOT NULL')).scalar_one():
            raise RuntimeError('Adult declarations exist; export/purge before downgrade')
    for table in ('household_memberships', 'households'):
        for column in ('adult_assurance', 'adult_statement_version', 'adult_declared_at'):
            op.drop_column(table, column)
