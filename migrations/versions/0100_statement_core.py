"""Synthetic statement core, exact ledger and immutable report evidence.

Revision ID: 0100
Revises: 0051
"""
import sqlalchemy as sa
from alembic import op

revision = "0100"
down_revision = "0051"
branch_labels = None
depends_on = None


def owned(name, *columns, constraints=()):
    op.create_table(name, sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), *columns, *constraints)
    op.create_index('ix_' + name + '_user_id', name, ['user_id'])


def col(name, typ, nullable=False):
    return sa.Column(name, typ, nullable=nullable)


def upgrade():
    owned('statement_accounts', col('label', sa.String(80)), col('token', sa.String(40)),
        col('account_type', sa.String(20)), col('revision', sa.Integer()), col('link_revision', sa.Integer()),
        constraints=(sa.UniqueConstraint('user_id', 'token', name='uq_statement_account_token'),))
    owned('statement_documents', col('account_id', sa.String(36)), col('digest', sa.String(64)),
        col('storage_key', sa.String(36)), col('size', sa.Integer()), col('created_at', sa.DateTime()),
        col('expires_at', sa.DateTime()), constraints=(sa.ForeignKeyConstraint(['account_id'], ['statement_accounts.id']),
        sa.UniqueConstraint('user_id', 'account_id', 'digest', name='uq_statement_digest')))
    owned('statement_imports', col('account_id', sa.String(36)), col('document_id', sa.String(36)),
        col('work_id', sa.String(36)), col('generation', sa.Integer()), col('revision', sa.Integer()),
        col('state', sa.String(24)), col('parser_version', sa.String(40)), col('checkpoint', sa.String(24)),
        col('error_code', sa.String(40), True), col('start_date', sa.String(10), True),
        col('end_date', sa.String(10), True), col('opening_paise', sa.BigInteger(), True),
        col('closing_paise', sa.BigInteger(), True), col('difference_paise', sa.BigInteger(), True),
        col('business_commit_id', sa.String(36), True), col('created_at', sa.DateTime()),
        constraints=(sa.ForeignKeyConstraint(['account_id'], ['statement_accounts.id']),
        sa.ForeignKeyConstraint(['document_id'], ['statement_documents.id']),
        sa.UniqueConstraint('document_id', 'generation', name='uq_statement_generation')))
    owned('statement_rows', col('import_id', sa.String(36)), col('ordinal', sa.Integer()),
        col('posting_date', sa.String(10)), col('amount_paise', sa.BigInteger()),
        col('description', sa.String(200)), col('reference', sa.String(80), True), col('category', sa.String(32)),
        constraints=(sa.ForeignKeyConstraint(['import_id'], ['statement_imports.id']),
        sa.UniqueConstraint('import_id', 'ordinal', name='uq_statement_row')))
    owned('ledger_entries', col('account_id', sa.String(36)), col('posting_date', sa.String(10)),
        col('amount_paise', sa.BigInteger()), col('description', sa.String(200)), col('reference', sa.String(80), True),
        col('components', sa.JSON()), col('active', sa.Boolean()), col('revision', sa.Integer()),
        constraints=(sa.ForeignKeyConstraint(['account_id'], ['statement_accounts.id']),))
    owned('ledger_evidence', col('entry_id', sa.String(36)), col('row_id', sa.String(36)),
        col('import_id', sa.String(36)), col('active', sa.Boolean()),
        constraints=(sa.ForeignKeyConstraint(['entry_id'], ['ledger_entries.id']),
        sa.ForeignKeyConstraint(['row_id'], ['statement_rows.id']),
        sa.ForeignKeyConstraint(['import_id'], ['statement_imports.id']),
        sa.UniqueConstraint('row_id', name='uq_ledger_evidence_row')))
    owned('ledger_corrections', col('account_id', sa.String(36)), col('target_id', sa.String(36)),
        col('operation_key', sa.String(64)), col('payload', sa.JSON()), col('before', sa.JSON()),
        col('after', sa.JSON()), col('created_at', sa.DateTime()),
        constraints=(sa.ForeignKeyConstraint(['account_id'], ['statement_accounts.id']),
        sa.UniqueConstraint('user_id', 'operation_key', name='uq_ledger_operation')))
    owned('ledger_links', col('left_id', sa.String(36)), col('right_id', sa.String(36)),
        col('kind', sa.String(24)), col('amount_paise', sa.BigInteger()), col('active', sa.Boolean()),
        constraints=(sa.ForeignKeyConstraint(['left_id'], ['ledger_entries.id']),
        sa.ForeignKeyConstraint(['right_id'], ['ledger_entries.id'])))
    owned('monthly_reports', col('month', sa.String(7)), col('rule_version', sa.String(24)),
        col('vector', sa.JSON()), col('snapshot', sa.JSON()), col('created_at', sa.DateTime()))
    # Origins, audit and published snapshots are append-only; privacy purge may DELETE.
    for table in ('statement_rows', 'ledger_corrections', 'monthly_reports'):
        if op.get_bind().dialect.name == 'sqlite':
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} "
                       "BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END")
        elif op.get_bind().dialect.name == 'postgresql':
            op.execute(f"CREATE FUNCTION {table}_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ "
                       "BEGIN RAISE EXCEPTION 'immutable evidence'; END; $$")
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} "
                       f"FOR EACH ROW EXECUTE FUNCTION {table}_no_update()")
        else:
            raise RuntimeError('unsupported statement database')


def downgrade():
    # Evidence must first be preserved/exported or purged through authorized lifecycle.
    tables = ('monthly_reports', 'ledger_links', 'ledger_corrections', 'ledger_evidence',
              'ledger_entries', 'statement_rows', 'statement_imports', 'statement_documents', 'statement_accounts')
    if any(op.get_bind().execute(sa.text(f'SELECT COUNT(*) FROM {table}')).scalar_one() for table in tables):
        raise RuntimeError('statement evidence exists; preserve/export before downgrade')
    for table in tables:
        # Explicit downgrade follows a separately verified backup; never used on live data here.
        if op.get_bind().dialect.name == 'postgresql' and table in ('monthly_reports', 'ledger_corrections', 'statement_rows'):
            op.execute(f'DROP TRIGGER {table}_immutable ON {table}')
            op.execute(f'DROP FUNCTION {table}_no_update()')
        op.drop_index('ix_' + table + '_user_id', table_name=table)
        op.drop_table(table)
