"""Encrypted mail payloads on the shared outbox; optional verified channel.

Revision ID: 0180
Revises: 0141
"""
from alembic import op
import sqlalchemy as sa

revision = '0180'
down_revision = '0141'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('notification_preferences', sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('notification_preferences', sa.Column('verified_email_hash', sa.String(64), nullable=True))
    op.create_table('mail_messages',
        sa.Column('id', sa.String(36), sa.ForeignKey('work_items.id'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('template_id', sa.String(40), nullable=False),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('first_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('state', sa.String(24), nullable=False),
        sa.Column('source_event', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_mail_messages_user_id', 'mail_messages', ['user_id'])


def downgrade():
    op.drop_index('ix_mail_messages_user_id', table_name='mail_messages')
    op.drop_table('mail_messages')
    op.drop_column('notification_preferences', 'verified_email_hash')
    op.drop_column('notification_preferences', 'email_enabled')
