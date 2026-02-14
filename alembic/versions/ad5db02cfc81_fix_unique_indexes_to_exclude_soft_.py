"""fix unique indexes to exclude soft-deleted rows

Revision ID: ad5db02cfc81
Revises: 623695dd5580
Create Date: 2026-02-14 12:03:05.257727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad5db02cfc81'
down_revision: Union[str, Sequence[str], None] = '623695dd5580'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old indexes
    op.drop_index('uq_budget_post_category', table_name='budget_posts')
    op.drop_index('uq_budget_post_transfer_accounts', table_name='budget_posts')

    # Create new indexes with deleted_at exclusion
    op.create_index(
        'uq_budget_post_category',
        'budget_posts',
        ['category_id'],
        unique=True,
        postgresql_where=sa.text('category_id IS NOT NULL AND deleted_at IS NULL')
    )
    op.create_index(
        'uq_budget_post_transfer_accounts',
        'budget_posts',
        ['transfer_from_account_id', 'transfer_to_account_id'],
        unique=True,
        postgresql_where=sa.text("direction = 'transfer' AND deleted_at IS NULL")
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new indexes
    op.drop_index('uq_budget_post_category', table_name='budget_posts')
    op.drop_index('uq_budget_post_transfer_accounts', table_name='budget_posts')

    # Recreate old indexes (without deleted_at exclusion)
    op.create_index(
        'uq_budget_post_category',
        'budget_posts',
        ['category_id'],
        unique=True,
        postgresql_where=sa.text('category_id IS NOT NULL')
    )
    op.create_index(
        'uq_budget_post_transfer_accounts',
        'budget_posts',
        ['transfer_from_account_id', 'transfer_to_account_id'],
        unique=True,
        postgresql_where=sa.text("direction = 'transfer'")
    )
