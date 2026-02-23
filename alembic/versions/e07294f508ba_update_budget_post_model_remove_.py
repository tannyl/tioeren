"""update_budget_post_model_remove_counterparty_add_account_ids

Revision ID: e07294f508ba
Revises: d823b759d6ea
Create Date: 2026-02-23 06:02:45.979907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'e07294f508ba'
down_revision: Union[str, Sequence[str], None] = 'd823b759d6ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove counterparty, add account_ids and via_account_id."""

    # Add new columns
    op.add_column('budget_posts', sa.Column('account_ids', JSONB, nullable=True))
    op.add_column('budget_posts', sa.Column('via_account_id', UUID(as_uuid=True), nullable=True))

    # Add foreign key for via_account_id
    op.create_foreign_key(
        'fk_budget_posts_via_account_id',
        'budget_posts',
        'accounts',
        ['via_account_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Data migration: Move counterparty_account_id to account_ids for account counterparty type
    # For external counterparty, we can't reliably migrate without amount pattern data, so leave as null
    op.execute("""
        UPDATE budget_posts
        SET account_ids = jsonb_build_array(counterparty_account_id::text)
        WHERE counterparty_type = 'account' AND counterparty_account_id IS NOT NULL
    """)

    # Drop foreign key constraint for counterparty_account_id
    op.drop_constraint('budget_posts_counterparty_account_id_fkey', 'budget_posts', type_='foreignkey')

    # Remove old counterparty columns
    op.drop_column('budget_posts', 'counterparty_account_id')
    op.drop_column('budget_posts', 'counterparty_type')

    # Drop the counterparty_type enum type (no columns use it anymore)
    op.execute("DROP TYPE IF EXISTS counterparty_type")


def downgrade() -> None:
    """Downgrade schema - restore counterparty, remove account_ids and via_account_id."""

    # Recreate the counterparty_type enum
    op.execute("CREATE TYPE counterparty_type AS ENUM ('external', 'account')")

    # Restore old counterparty columns
    op.add_column('budget_posts', sa.Column('counterparty_type', sa.Enum('external', 'account', name='counterparty_type'), nullable=True))
    op.add_column('budget_posts', sa.Column('counterparty_account_id', UUID(as_uuid=True), nullable=True))

    # Restore foreign key for counterparty_account_id
    op.create_foreign_key(
        'budget_posts_counterparty_account_id_fkey',
        'budget_posts',
        'accounts',
        ['counterparty_account_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # Data migration back: Extract first account from account_ids if it exists
    op.execute("""
        UPDATE budget_posts
        SET counterparty_type = 'account',
            counterparty_account_id = (account_ids->>0)::uuid
        WHERE account_ids IS NOT NULL
          AND jsonb_array_length(account_ids) >= 1
          AND direction IN ('income', 'expense')
    """)

    # For posts with no account_ids, assume external counterparty
    op.execute("""
        UPDATE budget_posts
        SET counterparty_type = 'external'
        WHERE direction IN ('income', 'expense')
          AND counterparty_type IS NULL
    """)

    # Drop foreign key constraint for via_account_id
    op.drop_constraint('fk_budget_posts_via_account_id', 'budget_posts', type_='foreignkey')

    # Remove new columns
    op.drop_column('budget_posts', 'via_account_id')
    op.drop_column('budget_posts', 'account_ids')
