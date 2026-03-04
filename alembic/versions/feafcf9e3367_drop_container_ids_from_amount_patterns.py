"""drop_container_ids_from_amount_patterns

Revision ID: feafcf9e3367
Revises: 1c606918e6bb
Create Date: 2026-03-04 06:20:02.167445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'feafcf9e3367'
down_revision: Union[str, Sequence[str], None] = '1c606918e6bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove container_ids from amount_patterns - containers now only on budget posts."""
    op.drop_column('amount_patterns', 'container_ids')


def downgrade() -> None:
    """Re-add container_ids to amount_patterns."""
    op.add_column('amount_patterns', sa.Column('container_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
