"""update_transaction_allocation_to_patterns_occurrences

Revision ID: 3fcbcddddbcf
Revises: ad5db02cfc81
Create Date: 2026-02-14 12:53:13.043080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fcbcddddbcf'
down_revision: Union[str, Sequence[str], None] = 'ad5db02cfc81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: replace budget_post_id with amount_pattern_id and amount_occurrence_id."""
    # Since this is pre-v1, we can delete existing allocation data
    op.execute("DELETE FROM transaction_allocations")

    # Drop old unique constraint
    op.drop_constraint('uq_transaction_allocation_transaction_budget_post', 'transaction_allocations', type_='unique')

    # Drop old budget_post_id column and index
    op.drop_column('transaction_allocations', 'budget_post_id')

    # Add new columns: amount_pattern_id and amount_occurrence_id (both nullable)
    op.add_column('transaction_allocations',
        sa.Column('amount_pattern_id', sa.UUID(), nullable=True)
    )
    op.add_column('transaction_allocations',
        sa.Column('amount_occurrence_id', sa.UUID(), nullable=True)
    )

    # Create foreign keys
    op.create_foreign_key(
        'fk_transaction_allocations_amount_pattern_id',
        'transaction_allocations',
        'amount_patterns',
        ['amount_pattern_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_transaction_allocations_amount_occurrence_id',
        'transaction_allocations',
        'amount_occurrences',
        ['amount_occurrence_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create indexes
    op.create_index(
        'ix_transaction_allocations_amount_pattern_id',
        'transaction_allocations',
        ['amount_pattern_id']
    )
    op.create_index(
        'ix_transaction_allocations_amount_occurrence_id',
        'transaction_allocations',
        ['amount_occurrence_id']
    )

    # Add CHECK constraint: exactly one of amount_pattern_id or amount_occurrence_id must be set
    op.create_check_constraint(
        'ck_transaction_allocation_exactly_one_target',
        'transaction_allocations',
        "(amount_pattern_id IS NOT NULL AND amount_occurrence_id IS NULL) OR "
        "(amount_pattern_id IS NULL AND amount_occurrence_id IS NOT NULL)"
    )

    # Create partial unique constraints (PostgreSQL)
    op.execute("""
        CREATE UNIQUE INDEX uq_transaction_allocation_transaction_pattern
        ON transaction_allocations (transaction_id, amount_pattern_id)
        WHERE amount_pattern_id IS NOT NULL
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_transaction_allocation_transaction_occurrence
        ON transaction_allocations (transaction_id, amount_occurrence_id)
        WHERE amount_occurrence_id IS NOT NULL
    """)

    # Drop updated_at column
    op.drop_column('transaction_allocations', 'updated_at')


def downgrade() -> None:
    """Downgrade schema: restore budget_post_id."""
    # Delete existing allocation data (pre-v1, destructive is OK)
    op.execute("DELETE FROM transaction_allocations")

    # Drop partial unique indexes
    op.drop_index('uq_transaction_allocation_transaction_occurrence', 'transaction_allocations')
    op.drop_index('uq_transaction_allocation_transaction_pattern', 'transaction_allocations')

    # Drop check constraint
    op.drop_constraint('ck_transaction_allocation_exactly_one_target', 'transaction_allocations', type_='check')

    # Drop indexes
    op.drop_index('ix_transaction_allocations_amount_occurrence_id', 'transaction_allocations')
    op.drop_index('ix_transaction_allocations_amount_pattern_id', 'transaction_allocations')

    # Drop foreign keys
    op.drop_constraint('fk_transaction_allocations_amount_occurrence_id', 'transaction_allocations', type_='foreignkey')
    op.drop_constraint('fk_transaction_allocations_amount_pattern_id', 'transaction_allocations', type_='foreignkey')

    # Drop new columns
    op.drop_column('transaction_allocations', 'amount_occurrence_id')
    op.drop_column('transaction_allocations', 'amount_pattern_id')

    # Re-add budget_post_id column
    op.add_column('transaction_allocations',
        sa.Column('budget_post_id', sa.UUID(), nullable=False)
    )

    # Re-create foreign key
    op.create_foreign_key(
        'fk_transaction_allocations_budget_post_id',
        'transaction_allocations',
        'budget_posts',
        ['budget_post_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Re-create index
    op.create_index(
        'ix_transaction_allocations_budget_post_id',
        'transaction_allocations',
        ['budget_post_id']
    )

    # Re-create unique constraint
    op.create_unique_constraint(
        'uq_transaction_allocation_transaction_budget_post',
        'transaction_allocations',
        ['transaction_id', 'budget_post_id']
    )

    # Re-add updated_at column
    op.add_column('transaction_allocations',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
