"""negate_positive_credit_limits

Revision ID: a78d2ddbd4a9
Revises: b948fad901ba
Create Date: 2026-02-23 16:54:51.102405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a78d2ddbd4a9'
down_revision: Union[str, Sequence[str], None] = 'b948fad901ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Negate positive credit_limit values to match SPEC semantics (negative = floor)
    # Values of 0 and NULL are left unchanged
    op.execute(
        "UPDATE accounts SET credit_limit = -credit_limit WHERE credit_limit > 0"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Restore original positive values
    op.execute(
        "UPDATE accounts SET credit_limit = -credit_limit WHERE credit_limit < 0"
    )
