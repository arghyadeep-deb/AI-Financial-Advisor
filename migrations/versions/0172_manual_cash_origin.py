"""Manual origins use the existing ledger, not a parallel transaction store."""
import sqlalchemy as sa
from alembic import op

revision = '0172'
down_revision = '0171'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ledger_entries', sa.Column('origin', sa.String(16), nullable=False, server_default='bank'))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM ledger_entries WHERE origin != 'bank'")).scalar_one():
        raise RuntimeError('Manual origin evidence exists; preserve/export or authorized purge before downgrade')
    op.drop_column('ledger_entries', 'origin')
