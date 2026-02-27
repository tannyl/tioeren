"""populate_null_pattern_container_ids

Revision ID: 1c606918e6bb
Revises: c66d2547ce8b
Create Date: 2026-02-27 05:24:54.273373

Data-only migration: populate null/empty container_ids in amount_patterns
for income/expense posts with the budget post's full container pool.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c606918e6bb'
down_revision: Union[str, Sequence[str], None] = 'c66d2547ce8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate null/empty container_ids with budget post's container pool."""
    connection = op.get_bind()

    result = connection.execute(sa.text("""
        UPDATE amount_patterns ap
        SET container_ids = bp.container_ids
        FROM budget_posts bp
        WHERE ap.budget_post_id = bp.id
          AND bp.direction IN ('income', 'expense')
          AND (ap.container_ids IS NULL OR ap.container_ids::text = '[]')
          AND bp.container_ids IS NOT NULL
          AND jsonb_array_length(bp.container_ids) > 0
    """))

    print(f"Updated {result.rowcount} amount patterns with budget post container pools")


def downgrade() -> None:
    """No downgrade - data migration is forward-only."""
    pass
