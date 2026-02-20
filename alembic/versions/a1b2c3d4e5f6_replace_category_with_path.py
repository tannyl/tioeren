"""replace_category_with_path

Revision ID: a1b2c3d4e5f6
Revises: 6d209312eed9
Create Date: 2026-02-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6d209312eed9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace Category entity with category_path and display_order arrays.

    This is a destructive migration - no downgrade path.
    """
    # 1. Add new columns to budget_posts
    op.add_column('budget_posts', sa.Column('category_path', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('budget_posts', sa.Column('display_order', postgresql.ARRAY(sa.Integer()), nullable=True))

    # 2. Add new columns to archived_budget_posts
    op.add_column('archived_budget_posts', sa.Column('category_path', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('archived_budget_posts', sa.Column('display_order', postgresql.ARRAY(sa.Integer()), nullable=True))

    # 3. Drop old unique index on budget_posts
    op.drop_index('uq_budget_post_category', table_name='budget_posts')

    # 4. Drop old unique index on archived_budget_posts
    op.drop_index('uq_archived_budget_post_category_period', table_name='archived_budget_posts')

    # 5. Drop category_id foreign key and column from budget_posts
    op.execute('ALTER TABLE budget_posts DROP CONSTRAINT IF EXISTS budget_posts_category_id_fkey')
    op.drop_column('budget_posts', 'category_id')

    # 6. Drop category_id foreign key and column from archived_budget_posts
    op.execute('ALTER TABLE archived_budget_posts DROP CONSTRAINT IF EXISTS archived_budget_posts_category_id_fkey')
    op.drop_column('archived_budget_posts', 'category_id')

    # 7. Drop categories table (cascades to budget.categories relationship)
    op.drop_table('categories')

    # 8. Create new unique index on budget_posts
    op.execute("""
        CREATE UNIQUE INDEX uq_budget_post_category_path
        ON budget_posts (budget_id, direction, category_path)
        WHERE category_path IS NOT NULL AND deleted_at IS NULL
    """)

    # 9. Create new unique index on archived_budget_posts
    op.execute("""
        CREATE UNIQUE INDEX uq_archived_budget_post_category_path_period
        ON archived_budget_posts (budget_id, direction, category_path, period_year, period_month)
        WHERE category_path IS NOT NULL
    """)


def downgrade() -> None:
    """No downgrade path - this is a destructive migration."""
    raise NotImplementedError("Downgrade not supported for category_path migration")
