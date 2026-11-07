"""Merge the Stage B (0004-0007) and modules (0050) migration branches.

Revision ID: 0051
Revises: 0007, 0050
"""
revision = "0051"
down_revision = ("0007", "0050")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass        # structural merge only: no schema change


def downgrade() -> None:
    pass
