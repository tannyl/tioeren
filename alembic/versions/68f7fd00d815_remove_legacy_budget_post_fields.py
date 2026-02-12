"""remove_legacy_budget_post_fields

Revision ID: 68f7fd00d815
Revises: b38537b697fa
Create Date: 2026-02-12 05:00:54.380187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68f7fd00d815'
down_revision: Union[str, Sequence[str], None] = 'b38537b697fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop legacy columns from budget_posts table
    # Data was already migrated to amount_patterns in previous migration
    op.drop_column('budget_posts', 'amount_min')
    op.drop_column('budget_posts', 'amount_max')
    op.drop_column('budget_posts', 'recurrence_pattern')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add legacy columns
    op.add_column('budget_posts', sa.Column('amount_min', sa.BigInteger(), nullable=True))
    op.add_column('budget_posts', sa.Column('amount_max', sa.BigInteger(), nullable=True))
    op.add_column('budget_posts', sa.Column('recurrence_pattern', sa.dialects.postgresql.JSONB(), nullable=True))

    # Backfill from first amount_pattern (best effort)
    op.execute("""
        UPDATE budget_posts bp
        SET
            amount_min = ap.amount,
            amount_max = ap.amount,
            recurrence_pattern = ap.recurrence_pattern
        FROM (
            SELECT DISTINCT ON (budget_post_id)
                budget_post_id,
                amount,
                recurrence_pattern
            FROM amount_patterns
            ORDER BY budget_post_id, start_date
        ) ap
        WHERE bp.id = ap.budget_post_id
    """)

    # Make amount_min non-nullable after backfill
    op.alter_column('budget_posts', 'amount_min', nullable=False)
