"""migrate_container_ids_to_allocation_objects

Convert container_ids JSONB from flat UUID array to array of allocation objects
with id, max_pct, and expected_pct fields.

Before: ["uuid1", "uuid2"]
After:  [{"id": "uuid1", "max_pct": 100, "expected_pct": 50}, {"id": "uuid2", "max_pct": 100, "expected_pct": 50}]

Revision ID: a1b2c3d4e5f7
Revises: feafcf9e3367
Create Date: 2026-03-08 12:00:00.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'feafcf9e3367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert container_ids from flat UUID array to allocation object array."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, container_ids FROM budget_posts WHERE container_ids IS NOT NULL")
    ).fetchall()

    for row in rows:
        post_id = row[0]
        raw = row[1]

        # Skip JSON null or non-list values
        if not isinstance(raw, list) or len(raw) == 0:
            continue

        # Skip if already migrated (first element is dict)
        if isinstance(raw[0], dict):
            continue

        # Convert flat UUID strings to allocation objects
        n = len(raw)
        sorted_ids = sorted(raw)
        allocations = []
        for uuid_str in sorted_ids:
            if n == 1:
                expected_pct = 100
            else:
                base = 100 // n
                remainder = 100 % n
                expected_pct = base + (remainder if uuid_str == sorted_ids[0] else 0)
            allocations.append({
                "id": uuid_str,
                "max_pct": 100,
                "expected_pct": expected_pct,
            })

        conn.execute(
            sa.text("UPDATE budget_posts SET container_ids = :val WHERE id = :id"),
            {"val": json.dumps(allocations), "id": post_id},
        )


def downgrade() -> None:
    """Convert container_ids back from allocation objects to flat UUID array."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, container_ids FROM budget_posts WHERE container_ids IS NOT NULL")
    ).fetchall()

    for row in rows:
        post_id = row[0]
        raw = row[1]

        if not isinstance(raw, list) or len(raw) == 0:
            continue

        # Skip if already flat strings
        if not isinstance(raw[0], dict):
            continue

        flat_ids = sorted(obj["id"] for obj in raw)
        conn.execute(
            sa.text("UPDATE budget_posts SET container_ids = :val WHERE id = :id"),
            {"val": json.dumps(flat_ids), "id": post_id},
        )
