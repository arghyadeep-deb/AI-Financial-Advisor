"""User-reported dated credit scores (feature 005 manual path)."""
import sqlalchemy as sa
from alembic import op
revision = '0220'
down_revision = '0202'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('manual_credit_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('bureau_label', sa.String(40), nullable=True),
        sa.Column('as_of', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM manual_credit_entries')).scalar_one():
        raise RuntimeError('Manual credit entries exist; export/purge before downgrade')
    op.drop_table('manual_credit_entries')
