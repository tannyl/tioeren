"""rename_accounts_to_containers

Revision ID: f1a2b3c4d5e6
Revises: a78d2ddbd4a9
Create Date: 2026-02-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a78d2ddbd4a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate accounts → containers with full schema transformation."""

    # =========================================================================
    # PHASE 1: Add currency to budgets table
    # =========================================================================
    op.add_column('budgets', sa.Column('currency', sa.String(3), nullable=False, server_default='DKK'))

    # =========================================================================
    # PHASE 2: Drop all foreign keys pointing TO accounts (from other tables)
    # =========================================================================

    # budget_posts FKs
    op.drop_constraint('budget_posts_transfer_from_account_id_fkey', 'budget_posts', type_='foreignkey')
    op.drop_constraint('budget_posts_transfer_from_account_id_fkey1', 'budget_posts', type_='foreignkey')
    op.drop_constraint('budget_posts_transfer_to_account_id_fkey', 'budget_posts', type_='foreignkey')
    op.drop_constraint('budget_posts_transfer_to_account_id_fkey1', 'budget_posts', type_='foreignkey')
    op.drop_constraint('fk_budget_posts_via_account_id', 'budget_posts', type_='foreignkey')

    # transactions FK
    op.drop_constraint('transactions_account_id_fkey', 'transactions', type_='foreignkey')

    # =========================================================================
    # PHASE 3: Drop indexes on columns we're about to rename
    # =========================================================================
    op.drop_index('ix_budget_posts_transfer_from_account_id', table_name='budget_posts')
    op.drop_index('ix_budget_posts_transfer_to_account_id', table_name='budget_posts')
    op.drop_index('ix_budget_posts_via_account_id', table_name='budget_posts')
    op.drop_index('uq_budget_post_transfer_accounts', table_name='budget_posts')
    op.drop_index('ix_transactions_account_id', table_name='transactions')

    # =========================================================================
    # PHASE 4: Rename columns in budget_posts
    # =========================================================================
    op.alter_column('budget_posts', 'account_ids', new_column_name='container_ids')
    op.alter_column('budget_posts', 'via_account_id', new_column_name='via_container_id')
    op.alter_column('budget_posts', 'transfer_from_account_id', new_column_name='transfer_from_container_id')
    op.alter_column('budget_posts', 'transfer_to_account_id', new_column_name='transfer_to_container_id')

    # =========================================================================
    # PHASE 5: Rename column in amount_patterns
    # =========================================================================
    op.alter_column('amount_patterns', 'account_ids', new_column_name='container_ids')

    # =========================================================================
    # PHASE 6: Rename column in transactions
    # =========================================================================
    op.alter_column('transactions', 'account_id', new_column_name='container_id')

    # =========================================================================
    # PHASE 7: Transform the accounts table itself
    # =========================================================================

    # 7a. Add new columns before renaming table
    op.add_column('accounts', sa.Column('bank_name', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('bank_account_name', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('bank_reg_number', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('bank_account_number', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('overdraft_limit', sa.BigInteger(), nullable=True))
    op.add_column('accounts', sa.Column('allow_withdrawals', sa.Boolean(), nullable=True))
    op.add_column('accounts', sa.Column('interest_rate', sa.Numeric(), nullable=True))
    op.add_column('accounts', sa.Column('interest_frequency', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('required_payment', sa.BigInteger(), nullable=True))

    # 7b. Migrate credit_limit → overdraft_limit for accounts becoming cashbox (currently normal)
    # Normal accounts with credit_limit set → move to overdraft_limit
    op.execute("""
        UPDATE accounts
        SET overdraft_limit = credit_limit,
            credit_limit = NULL
        WHERE purpose = 'normal' AND credit_limit IS NOT NULL
    """)

    # 7c. NULL out credit_limit for savings accounts (becoming piggybank)
    op.execute("""
        UPDATE accounts
        SET credit_limit = NULL
        WHERE purpose = 'savings'
    """)

    # 7d. For kassekredit accounts becoming debt, set allow_withdrawals = true
    op.execute("""
        UPDATE accounts
        SET allow_withdrawals = true
        WHERE purpose = 'kassekredit'
    """)

    # 7e. For loan accounts becoming debt, set allow_withdrawals = false
    op.execute("""
        UPDATE accounts
        SET allow_withdrawals = false
        WHERE purpose = 'loan'
    """)

    # 7f. Make locked nullable (was NOT NULL, now only relevant for piggybank)
    op.alter_column('accounts', 'locked', nullable=True)

    # 7g. NULL out locked for non-savings accounts
    op.execute("""
        UPDATE accounts
        SET locked = NULL
        WHERE purpose != 'savings'
    """)

    # 7h. Populate bank_name from datasource for bank accounts
    op.execute("""
        UPDATE accounts
        SET bank_name = 'Ukendt bank'
        WHERE datasource = 'bank'
    """)

    # 7i. Drop datasource column and enum
    op.drop_column('accounts', 'datasource')
    op.execute("DROP TYPE account_datasource")

    # 7j. Drop currency column (moved to budget level)
    op.drop_column('accounts', 'currency')

    # =========================================================================
    # PHASE 8: Create new container_type enum and migrate purpose → type
    # =========================================================================

    # 8a. Create the new enum
    op.execute("CREATE TYPE container_type AS ENUM ('cashbox', 'piggybank', 'debt')")

    # 8b. Add temporary 'type' column with new enum
    op.add_column('accounts', sa.Column(
        'type',
        sa.Enum('cashbox', 'piggybank', 'debt', name='container_type', create_type=False),
        nullable=True,
    ))

    # 8c. Migrate data: purpose → type
    op.execute("""
        UPDATE accounts SET type = 'cashbox' WHERE purpose = 'normal'
    """)
    op.execute("""
        UPDATE accounts SET type = 'piggybank' WHERE purpose = 'savings'
    """)
    op.execute("""
        UPDATE accounts SET type = 'debt' WHERE purpose IN ('loan', 'kassekredit')
    """)

    # 8d. Make type NOT NULL
    op.alter_column('accounts', 'type', nullable=False)

    # 8e. Drop purpose column and old enum
    op.drop_column('accounts', 'purpose')
    op.execute("DROP TYPE account_purpose")

    # =========================================================================
    # PHASE 9: Rename table accounts → containers
    # =========================================================================
    op.rename_table('accounts', 'containers')

    # =========================================================================
    # PHASE 10: Rename accounts constraints and indexes
    # =========================================================================

    # Rename PK constraint
    op.execute("ALTER INDEX accounts_pkey RENAME TO containers_pkey")

    # Rename budget_id index
    op.execute("ALTER INDEX ix_accounts_budget_id RENAME TO ix_containers_budget_id")

    # Rename FK constraints on containers table
    op.execute("ALTER TABLE containers RENAME CONSTRAINT accounts_budget_id_fkey TO containers_budget_id_fkey")
    op.execute("ALTER TABLE containers RENAME CONSTRAINT accounts_created_by_fkey TO containers_created_by_fkey")
    op.execute("ALTER TABLE containers RENAME CONSTRAINT accounts_updated_by_fkey TO containers_updated_by_fkey")

    # =========================================================================
    # PHASE 11: Recreate foreign keys pointing to containers
    # =========================================================================

    # budget_posts FKs
    op.create_foreign_key(
        'fk_budget_posts_via_container_id',
        'budget_posts', 'containers',
        ['via_container_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_budget_posts_transfer_from_container_id',
        'budget_posts', 'containers',
        ['transfer_from_container_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_budget_posts_transfer_to_container_id',
        'budget_posts', 'containers',
        ['transfer_to_container_id'], ['id'],
        ondelete='CASCADE',
    )

    # transactions FK
    op.create_foreign_key(
        'fk_transactions_container_id',
        'transactions', 'containers',
        ['container_id'], ['id'],
        ondelete='CASCADE',
    )

    # =========================================================================
    # PHASE 12: Recreate indexes
    # =========================================================================
    op.create_index('ix_budget_posts_via_container_id', 'budget_posts', ['via_container_id'])
    op.create_index('ix_budget_posts_transfer_from_container_id', 'budget_posts', ['transfer_from_container_id'])
    op.create_index('ix_budget_posts_transfer_to_container_id', 'budget_posts', ['transfer_to_container_id'])
    op.create_index('ix_transactions_container_id', 'transactions', ['container_id'])

    # Unique index for transfer pairs
    op.execute("""
        CREATE UNIQUE INDEX uq_budget_post_transfer_containers
        ON budget_posts (transfer_from_container_id, transfer_to_container_id)
        WHERE direction = 'transfer' AND deleted_at IS NULL
    """)


def downgrade() -> None:
    """No downgrade - destructive migration."""
    raise NotImplementedError("Downgrade not supported for accounts→containers migration")
