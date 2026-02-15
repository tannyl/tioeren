"""migrate_postpone_weekend_to_bank_day_adjustment

Revision ID: 6d209312eed9
Revises: 3fcbcddddbcf
Create Date: 2026-02-14 22:45:31.065691

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d209312eed9'
down_revision: Union[str, Sequence[str], None] = '3fcbcddddbcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate postpone_weekend to bank_day_adjustment in JSONB data.

    Transform recurrence_pattern JSONB field in amount_patterns table:
    - postpone_weekend: true -> bank_day_adjustment: "next"
    - postpone_weekend: false -> remove field (default is "none")
    """
    # Convert postpone_weekend: true to bank_day_adjustment: "next"
    op.execute("""
        UPDATE amount_patterns
        SET recurrence_pattern = (recurrence_pattern - 'postpone_weekend') || '{"bank_day_adjustment": "next"}'::jsonb
        WHERE recurrence_pattern ? 'postpone_weekend'
        AND (recurrence_pattern->>'postpone_weekend')::boolean = true
    """)

    # Remove postpone_weekend: false (default "none" needs no explicit field)
    op.execute("""
        UPDATE amount_patterns
        SET recurrence_pattern = recurrence_pattern - 'postpone_weekend'
        WHERE recurrence_pattern ? 'postpone_weekend'
        AND ((recurrence_pattern->>'postpone_weekend')::boolean = false OR recurrence_pattern->>'postpone_weekend' IS NULL)
    """)


def downgrade() -> None:
    """Revert bank_day_adjustment to postpone_weekend.

    Transform recurrence_pattern JSONB field in amount_patterns table:
    - bank_day_adjustment: "next" -> postpone_weekend: true
    - bank_day_adjustment: "previous" -> postpone_weekend: true (closest approximation)
    - bank_day_adjustment: "none" -> remove field (same as no postpone_weekend)
    """
    # Convert bank_day_adjustment: "next" back to postpone_weekend: true
    op.execute("""
        UPDATE amount_patterns
        SET recurrence_pattern = (recurrence_pattern - 'bank_day_adjustment') || '{"postpone_weekend": true}'::jsonb
        WHERE recurrence_pattern ? 'bank_day_adjustment'
        AND recurrence_pattern->>'bank_day_adjustment' = 'next'
    """)

    # Convert bank_day_adjustment: "previous" back to postpone_weekend: true (closest approximation)
    op.execute("""
        UPDATE amount_patterns
        SET recurrence_pattern = (recurrence_pattern - 'bank_day_adjustment') || '{"postpone_weekend": true}'::jsonb
        WHERE recurrence_pattern ? 'bank_day_adjustment'
        AND recurrence_pattern->>'bank_day_adjustment' = 'previous'
    """)

    # Remove bank_day_adjustment: "none" (same as no postpone_weekend)
    op.execute("""
        UPDATE amount_patterns
        SET recurrence_pattern = recurrence_pattern - 'bank_day_adjustment'
        WHERE recurrence_pattern ? 'bank_day_adjustment'
        AND recurrence_pattern->>'bank_day_adjustment' = 'none'
    """)

