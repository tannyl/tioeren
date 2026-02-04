"""create budget_posts table

Revision ID: 75bf45033d9c
Revises: 9d0f687d98b3
Create Date: 2026-02-04 14:38:04.498042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '75bf45033d9c'
down_revision: Union[str, Sequence[str], None] = '9d0f687d98b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create budget_posts table
    op.create_table(
        'budget_posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('budget_id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.Enum('fixed', 'ceiling', 'rolling', name='budget_post_type'), nullable=False),
        sa.Column('amount_min', sa.BigInteger(), nullable=False),
        sa.Column('amount_max', sa.BigInteger(), nullable=True),
        sa.Column('from_account_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('to_account_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recurrence_pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_budget_posts_budget_id'), 'budget_posts', ['budget_id'], unique=False)
    op.create_index(op.f('ix_budget_posts_category_id'), 'budget_posts', ['category_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f('ix_budget_posts_category_id'), table_name='budget_posts')
    op.drop_index(op.f('ix_budget_posts_budget_id'), table_name='budget_posts')

    # Drop table
    op.drop_table('budget_posts')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS budget_post_type CASCADE')
