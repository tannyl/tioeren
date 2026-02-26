"""remove_budget_post_type_and_fixed_expenses

Revision ID: c66d2547ce8b
Revises: f1a2b3c4d5e6
Create Date: 2026-02-26 18:27:12.837324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c66d2547ce8b'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop type column from budget_posts
    op.drop_column('budget_posts', 'type')

    # Drop type column from archived_budget_posts
    op.drop_column('archived_budget_posts', 'type')

    # Drop the budget_post_type enum type
    op.execute("DROP TYPE IF EXISTS budget_post_type")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the enum type
    op.execute("CREATE TYPE budget_post_type AS ENUM ('fixed', 'ceiling')")

    # Add type column back to budget_posts
    op.add_column('budget_posts',
        sa.Column('type', sa.Enum('fixed', 'ceiling', name='budget_post_type', native_enum=True), nullable=False, server_default='ceiling')
    )

    # Add type column back to archived_budget_posts
    op.add_column('archived_budget_posts',
        sa.Column('type', sa.Enum('fixed', 'ceiling', name='budget_post_type', native_enum=True), nullable=False, server_default='ceiling')
    )
