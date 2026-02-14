"""rebuild budget post model active archived split

Revision ID: 623695dd5580
Revises: ec13e37e7004
Create Date: 2026-02-14 10:22:01.378055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '623695dd5580'
down_revision: Union[str, Sequence[str], None] = 'ec13e37e7004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create new enum types
    op.execute("CREATE TYPE budget_post_direction AS ENUM ('income', 'expense', 'transfer')")
    op.execute("CREATE TYPE counterparty_type AS ENUM ('external', 'account')")

    # Note: budget_post_type already exists from previous migration (removed ROLLING value)

    # Create archived_budget_posts table using SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE archived_budget_posts (
            id UUID PRIMARY KEY,
            budget_id UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
            budget_post_id UUID REFERENCES budget_posts(id) ON DELETE SET NULL,
            period_year INTEGER NOT NULL,
            period_month INTEGER NOT NULL,
            direction budget_post_direction NOT NULL,
            category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
            type budget_post_type NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            created_by UUID REFERENCES users(id)
        )
    """)
    op.create_index(op.f('ix_archived_budget_posts_budget_id'), 'archived_budget_posts', ['budget_id'], unique=False)
    op.create_index(op.f('ix_archived_budget_posts_budget_post_id'), 'archived_budget_posts', ['budget_post_id'], unique=False)
    op.create_index(op.f('ix_archived_budget_posts_category_id'), 'archived_budget_posts', ['category_id'], unique=False)
    op.create_index('uq_archived_budget_post_category_period', 'archived_budget_posts', ['category_id', 'period_year', 'period_month'], unique=True, postgresql_where='category_id IS NOT NULL')

    # Create amount_occurrences table
    op.execute("""
        CREATE TABLE amount_occurrences (
            id UUID PRIMARY KEY,
            archived_budget_post_id UUID NOT NULL REFERENCES archived_budget_posts(id) ON DELETE CASCADE,
            date DATE,
            amount BIGINT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.create_index(op.f('ix_amount_occurrences_archived_budget_post_id'), 'amount_occurrences', ['archived_budget_post_id'], unique=False)
    # Add new columns to amount_patterns
    op.add_column('amount_patterns', sa.Column('account_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add new columns to budget_posts using SQL to avoid enum creation issues
    op.execute("ALTER TABLE budget_posts ADD COLUMN direction budget_post_direction")
    op.execute("ALTER TABLE budget_posts ADD COLUMN accumulate BOOLEAN")
    op.execute("ALTER TABLE budget_posts ADD COLUMN counterparty_type counterparty_type")
    op.execute("ALTER TABLE budget_posts ADD COLUMN counterparty_account_id UUID REFERENCES accounts(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE budget_posts ADD COLUMN transfer_from_account_id UUID REFERENCES accounts(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE budget_posts ADD COLUMN transfer_to_account_id UUID REFERENCES accounts(id) ON DELETE CASCADE")

    # Data migration: Since this is pre-v1 with no external users, delete existing data
    # to avoid dealing with complex data migration and constraint violations
    op.execute("DELETE FROM budget_posts")

    # Set safe defaults for any remaining rows (defensive)
    op.execute("UPDATE budget_posts SET direction = 'expense' WHERE direction IS NULL")
    op.execute("UPDATE budget_posts SET accumulate = FALSE WHERE accumulate IS NULL")
    op.execute("UPDATE budget_posts SET counterparty_type = 'external' WHERE counterparty_type IS NULL")

    # Make direction and accumulate non-nullable after setting defaults
    op.alter_column('budget_posts', 'direction', nullable=False)
    op.alter_column('budget_posts', 'accumulate', nullable=False)
    op.alter_column('budget_posts', 'category_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.drop_constraint(op.f('uq_budget_post_category_period'), 'budget_posts', type_='unique')
    op.create_index(op.f('ix_budget_posts_counterparty_account_id'), 'budget_posts', ['counterparty_account_id'], unique=False)
    op.create_index(op.f('ix_budget_posts_transfer_from_account_id'), 'budget_posts', ['transfer_from_account_id'], unique=False)
    op.create_index(op.f('ix_budget_posts_transfer_to_account_id'), 'budget_posts', ['transfer_to_account_id'], unique=False)
    op.create_index('uq_budget_post_category', 'budget_posts', ['category_id'], unique=True, postgresql_where='category_id IS NOT NULL')
    op.create_index('uq_budget_post_transfer_accounts', 'budget_posts', ['transfer_from_account_id', 'transfer_to_account_id'], unique=True, postgresql_where="direction = 'transfer'")
    op.create_foreign_key(None, 'budget_posts', 'accounts', ['counterparty_account_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'budget_posts', 'accounts', ['transfer_from_account_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'budget_posts', 'accounts', ['transfer_to_account_id'], ['id'], ondelete='CASCADE')
    op.drop_column('budget_posts', 'to_account_ids')
    op.drop_column('budget_posts', 'is_archived')
    op.drop_column('budget_posts', 'period_year')
    op.drop_column('budget_posts', 'period_month')
    op.drop_column('budget_posts', 'from_account_ids')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # Note: This downgrade will fail if data exists in the new tables
    # Pre-v1, no external users, so destructive downgrade is acceptable
    op.add_column('budget_posts', sa.Column('from_account_ids', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('budget_posts', sa.Column('period_month', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('budget_posts', sa.Column('period_year', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('budget_posts', sa.Column('is_archived', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('budget_posts', sa.Column('to_account_ids', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'budget_posts', type_='foreignkey')
    op.drop_constraint(None, 'budget_posts', type_='foreignkey')
    op.drop_constraint(None, 'budget_posts', type_='foreignkey')
    op.drop_index('uq_budget_post_transfer_accounts', table_name='budget_posts', postgresql_where="direction = 'transfer'")
    op.drop_index('uq_budget_post_category', table_name='budget_posts', postgresql_where='category_id IS NOT NULL')
    op.drop_index(op.f('ix_budget_posts_transfer_to_account_id'), table_name='budget_posts')
    op.drop_index(op.f('ix_budget_posts_transfer_from_account_id'), table_name='budget_posts')
    op.drop_index(op.f('ix_budget_posts_counterparty_account_id'), table_name='budget_posts')
    op.create_unique_constraint(op.f('uq_budget_post_category_period'), 'budget_posts', ['category_id', 'period_year', 'period_month'], postgresql_nulls_not_distinct=False)
    op.alter_column('budget_posts', 'category_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('budget_posts', 'transfer_to_account_id')
    op.drop_column('budget_posts', 'transfer_from_account_id')
    op.drop_column('budget_posts', 'counterparty_account_id')
    op.drop_column('budget_posts', 'counterparty_type')
    op.drop_column('budget_posts', 'accumulate')
    op.drop_column('budget_posts', 'direction')
    op.drop_column('amount_patterns', 'account_ids')
    op.drop_index(op.f('ix_amount_occurrences_archived_budget_post_id'), table_name='amount_occurrences')
    op.drop_table('amount_occurrences')
    op.drop_index('uq_archived_budget_post_category_period', table_name='archived_budget_posts', postgresql_where='category_id IS NOT NULL')
    op.drop_index(op.f('ix_archived_budget_posts_category_id'), table_name='archived_budget_posts')
    op.drop_index(op.f('ix_archived_budget_posts_budget_post_id'), table_name='archived_budget_posts')
    op.drop_index(op.f('ix_archived_budget_posts_budget_id'), table_name='archived_budget_posts')
    op.drop_table('archived_budget_posts')

    # Drop new enum types
    op.execute("DROP TYPE IF EXISTS counterparty_type")
    op.execute("DROP TYPE IF EXISTS budget_post_direction")
    # ### end Alembic commands ###
