"""create transaction_allocations table

Revision ID: b117ef9965b8
Revises: 75bf45033d9c
Create Date: 2026-02-04 14:59:05.944143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b117ef9965b8'
down_revision: Union[str, Sequence[str], None] = '75bf45033d9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create transaction_allocations table
    op.create_table(
        'transaction_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('budget_post_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('is_remainder', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['budget_post_id'], ['budget_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id', 'budget_post_id', name='uq_transaction_allocation_transaction_budget_post')
    )

    # Create indexes
    op.create_index(op.f('ix_transaction_allocations_transaction_id'), 'transaction_allocations', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_transaction_allocations_budget_post_id'), 'transaction_allocations', ['budget_post_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f('ix_transaction_allocations_budget_post_id'), table_name='transaction_allocations')
    op.drop_index(op.f('ix_transaction_allocations_transaction_id'), table_name='transaction_allocations')

    # Drop table
    op.drop_table('transaction_allocations')
