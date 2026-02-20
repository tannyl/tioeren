"""Budget service layer for business logic."""

import base64
import json
import uuid
from datetime import datetime, UTC

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.models.budget import Budget


def create_budget(
    db: Session,
    name: str,
    owner_id: uuid.UUID,
    warning_threshold: int | None = None,
) -> Budget:
    """
    Create a new budget.

    New budgets start empty - no default categories or posts.

    Args:
        db: Database session
        name: Budget name
        owner_id: User ID who owns the budget
        warning_threshold: Optional warning threshold in øre

    Returns:
        Created Budget instance
    """
    budget = Budget(
        name=name,
        owner_id=owner_id,
        warning_threshold=warning_threshold,
        created_by=owner_id,
        updated_by=owner_id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    return budget


def encode_cursor(created_at: datetime, budget_id: uuid.UUID) -> str:
    """
    Encode pagination cursor from created_at and id.

    Args:
        created_at: Budget creation timestamp
        budget_id: Budget UUID

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "created_at": created_at.isoformat(),
        "id": str(budget_id),
    }
    cursor_json = json.dumps(cursor_data)
    return base64.urlsafe_b64encode(cursor_json.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """
    Decode pagination cursor to created_at and id.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (created_at, budget_id)

    Raises:
        ValueError: If cursor is invalid
    """
    try:
        cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
        cursor_data = json.loads(cursor_json)
        created_at = datetime.fromisoformat(cursor_data["created_at"])
        budget_id = uuid.UUID(cursor_data["id"])
        return created_at, budget_id
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid cursor: {e}")


def get_user_budgets(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[Budget], str | None]:
    """
    Get paginated list of budgets for a user.

    Args:
        db: Database session
        user_id: User ID to get budgets for
        limit: Maximum number of items to return
        cursor: Optional cursor for pagination

    Returns:
        Tuple of (list of budgets, next cursor or None)
    """
    query = db.query(Budget).filter(
        Budget.owner_id == user_id,
        Budget.deleted_at.is_(None),
    )

    # Apply cursor if provided
    if cursor:
        try:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            # For descending order: (created_at < cursor_created_at) OR (created_at = cursor_created_at AND id < cursor_id)
            query = query.filter(
                or_(
                    Budget.created_at < cursor_created_at,
                    and_(
                        Budget.created_at == cursor_created_at,
                        Budget.id < cursor_id,
                    ),
                )
            )
        except ValueError:
            # Invalid cursor, return empty result
            return [], None

    # Sort by created_at DESC, then id DESC for stable ordering
    query = query.order_by(Budget.created_at.desc(), Budget.id.desc())

    # Fetch limit + 1 to check if there are more items
    budgets = query.limit(limit + 1).all()

    # Determine next cursor
    next_cursor = None
    if len(budgets) > limit:
        last_budget = budgets[limit - 1]
        next_cursor = encode_cursor(last_budget.created_at, last_budget.id)
        budgets = budgets[:limit]

    return budgets, next_cursor


def get_budget_by_id(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Budget | None:
    """
    Get a single budget by ID with ownership check.

    Args:
        db: Database session
        budget_id: Budget ID to retrieve
        user_id: User ID to verify ownership

    Returns:
        Budget if found and owned by user, None otherwise
    """
    return db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.owner_id == user_id,
        Budget.deleted_at.is_(None),
    ).first()


def update_budget(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str | None = None,
    warning_threshold: int | None = None,
) -> Budget | None:
    """
    Update a budget.

    Args:
        db: Database session
        budget_id: Budget ID to update
        user_id: User ID to verify ownership
        name: Optional new name
        warning_threshold: Optional new warning threshold

    Returns:
        Updated Budget if found and owned by user, None otherwise
    """
    budget = get_budget_by_id(db, budget_id, user_id)
    if not budget:
        return None

    if name is not None:
        budget.name = name
    if warning_threshold is not None:
        budget.warning_threshold = warning_threshold

    budget.updated_by = user_id

    db.commit()
    db.refresh(budget)

    return budget


def soft_delete_budget(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Soft delete a budget.

    Args:
        db: Database session
        budget_id: Budget ID to delete
        user_id: User ID to verify ownership

    Returns:
        True if budget was deleted, False if not found or not owned
    """
    budget = get_budget_by_id(db, budget_id, user_id)
    if not budget:
        return False

    budget.deleted_at = datetime.now(UTC)
    db.commit()

    return True
