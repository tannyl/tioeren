"""update_account_model

Revision ID: d823b759d6ea
Revises: a1b2c3d4e5f6
Create Date: 2026-02-23 05:43:40.460050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd823b759d6ea'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update Account model: add kassekredit purpose, remove credit datasource,
    replace can_go_negative with credit_limit, add locked, remove needs_coverage."""

    # 1. Add 'kassekredit' value to AccountPurpose enum
    # Note: ALTER TYPE ADD VALUE cannot run inside a transaction block.
    # Alembic wraps migrations in transactions by default, so we must use autocommit_block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE account_purpose ADD VALUE 'kassekredit'")

    # 2. Remove 'credit' from AccountDatasource enum
    # PostgreSQL doesn't support DROP VALUE, so we need to recreate the enum

    # 2a. Create new enum type without 'credit'
    op.execute("""
        CREATE TYPE account_datasource_new AS ENUM ('bank', 'cash', 'virtual')
    """)

    # 2b. Migrate any existing 'credit' accounts to 'bank' (there are none, but safe to include)
    op.execute("""
        UPDATE accounts
        SET datasource = 'bank'::account_datasource
        WHERE datasource = 'credit'::account_datasource
    """)

    # 2c. Alter column to use new enum (with USING clause for type conversion)
    op.execute("""
        ALTER TABLE accounts
        ALTER COLUMN datasource TYPE account_datasource_new
        USING datasource::text::account_datasource_new
    """)

    # 2d. Drop old enum type
    op.execute("DROP TYPE account_datasource")

    # 2e. Rename new enum type to original name
    op.execute("ALTER TYPE account_datasource_new RENAME TO account_datasource")

    # 3. Add credit_limit column (BIGINT, nullable)
    op.add_column('accounts', sa.Column('credit_limit', sa.BigInteger(), nullable=True))

    # 4. Migrate data from can_go_negative to credit_limit
    # can_go_negative=False → credit_limit=0 (cannot go negative)
    # can_go_negative=True → credit_limit=NULL (no limit set/unknown)
    op.execute("""
        UPDATE accounts
        SET credit_limit = CASE
            WHEN can_go_negative = false THEN 0
            ELSE NULL
        END
    """)

    # 5. Drop can_go_negative column
    op.drop_column('accounts', 'can_go_negative')

    # 6. Add locked column (BOOLEAN, NOT NULL, default False)
    op.add_column('accounts', sa.Column('locked', sa.Boolean(), nullable=False, server_default='false'))

    # 7. Remove needs_coverage column
    op.drop_column('accounts', 'needs_coverage')


def downgrade() -> None:
    """No downgrade path - this is a destructive migration."""
    raise NotImplementedError("Downgrade not supported for account model update")
