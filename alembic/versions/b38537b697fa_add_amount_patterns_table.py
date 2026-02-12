"""add_amount_patterns_table

Revision ID: b38537b697fa
Revises: b117ef9965b8
Create Date: 2026-02-11 21:20:51.478833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'b38537b697fa'
down_revision: Union[str, Sequence[str], None] = 'b117ef9965b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create amount_patterns table
    op.create_table(
        'amount_patterns',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('budget_post_id', UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('recurrence_pattern', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['budget_post_id'], ['budget_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )

    # Create index on budget_post_id for faster lookups
    op.create_index('ix_amount_patterns_budget_post_id', 'amount_patterns', ['budget_post_id'])

    # Migrate existing budget posts to amount_patterns
    # For each budget post with amount_min and/or recurrence_pattern, create one AmountPattern
    op.execute("""
        INSERT INTO amount_patterns (id, budget_post_id, amount, start_date, end_date, recurrence_pattern, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            id,
            amount_min,
            created_at::date,
            NULL,
            recurrence_pattern,
            created_at,
            updated_at
        FROM budget_posts
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('ix_amount_patterns_budget_post_id', table_name='amount_patterns')

    # Drop amount_patterns table
    op.drop_table('amount_patterns')
