"""revise_budget_post_category_relationship

Revision ID: ec13e37e7004
Revises: 68f7fd00d815
Create Date: 2026-02-12 13:05:30.012473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec13e37e7004'
down_revision: Union[str, Sequence[str], None] = '68f7fd00d815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add period_year with current year as default
    op.execute("ALTER TABLE budget_posts ADD COLUMN period_year INTEGER NOT NULL DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)")

    # Add period_month with current month as default
    op.execute("ALTER TABLE budget_posts ADD COLUMN period_month INTEGER NOT NULL DEFAULT EXTRACT(MONTH FROM CURRENT_DATE)")

    # Add is_archived with default false
    op.add_column('budget_posts', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))

    # Remove server_default from period_year and period_month after backfilling
    op.alter_column('budget_posts', 'period_year', server_default=None)
    op.alter_column('budget_posts', 'period_month', server_default=None)

    # Clean up duplicates: For each (category_id, period_year, period_month) combination,
    # keep only the oldest budget_post (by created_at), delete the rest.
    # This is safe for pre-v1 development data.
    op.execute("""
        DELETE FROM budget_posts
        WHERE id NOT IN (
            SELECT DISTINCT ON (category_id, period_year, period_month) id
            FROM budget_posts
            ORDER BY category_id, period_year, period_month, created_at ASC
        )
    """)

    # Add UNIQUE constraint on (category_id, period_year, period_month)
    op.create_unique_constraint('uq_budget_post_category_period', 'budget_posts', ['category_id', 'period_year', 'period_month'])

    # Drop name column
    op.drop_column('budget_posts', 'name')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back name column (nullable initially)
    op.add_column('budget_posts', sa.Column('name', sa.String(length=255), nullable=True))

    # Backfill name from category
    op.execute("""
        UPDATE budget_posts bp
        SET name = c.name
        FROM categories c
        WHERE bp.category_id = c.id
    """)

    # Make name non-nullable after backfill
    op.alter_column('budget_posts', 'name', nullable=False)

    # Drop unique constraint
    op.drop_constraint('uq_budget_post_category_period', 'budget_posts', type_='unique')

    # Drop new columns
    op.drop_column('budget_posts', 'is_archived')
    op.drop_column('budget_posts', 'period_month')
    op.drop_column('budget_posts', 'period_year')
