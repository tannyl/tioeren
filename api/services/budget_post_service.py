"""Budget post service layer for business logic."""

import base64
import json
import uuid
from datetime import datetime, UTC

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.models.budget_post import BudgetPost, BudgetPostType
from api.models.category import Category
from api.models.account import Account


def encode_cursor(created_at: datetime, post_id: uuid.UUID) -> str:
    """
    Encode pagination cursor from created_at and id.

    Args:
        created_at: Budget post creation timestamp
        post_id: Budget post UUID

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "created_at": created_at.isoformat(),
        "id": str(post_id),
    }
    cursor_json = json.dumps(cursor_data)
    return base64.urlsafe_b64encode(cursor_json.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """
    Decode pagination cursor to created_at and id.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (created_at, post_id)

    Raises:
        ValueError: If cursor is invalid
    """
    try:
        cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
        cursor_data = json.loads(cursor_json)
        created_at = datetime.fromisoformat(cursor_data["created_at"])
        post_id = uuid.UUID(cursor_data["id"])
        return created_at, post_id
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid cursor: {e}")


def create_budget_post(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    name: str,
    post_type: BudgetPostType,
    amount_min: int,
    amount_max: int | None = None,
    from_account_ids: list[uuid.UUID] | None = None,
    to_account_ids: list[uuid.UUID] | None = None,
    recurrence_pattern: dict | None = None,
) -> BudgetPost | None:
    """
    Create a new budget post.

    Args:
        db: Database session
        budget_id: Budget UUID (must belong to user)
        user_id: User ID creating the post
        category_id: Category UUID (must belong to same budget)
        name: Budget post name
        post_type: Type of budget post
        amount_min: Minimum amount in øre
        amount_max: Maximum amount in øre (optional)
        from_account_ids: List of source account UUIDs (optional)
        to_account_ids: List of destination account UUIDs (optional)
        recurrence_pattern: Recurrence configuration dict (optional)

    Returns:
        Created BudgetPost instance, or None if validation fails
    """
    # Verify category belongs to the same budget
    category = db.query(Category).filter(
        and_(
            Category.id == category_id,
            Category.budget_id == budget_id,
            Category.deleted_at.is_(None),
        )
    ).first()

    if not category:
        return None

    # Verify all from_account_ids belong to the budget
    if from_account_ids:
        from_accounts = db.query(Account).filter(
            and_(
                Account.id.in_(from_account_ids),
                Account.budget_id == budget_id,
                Account.deleted_at.is_(None),
            )
        ).all()
        if len(from_accounts) != len(from_account_ids):
            return None

    # Verify all to_account_ids belong to the budget
    if to_account_ids:
        to_accounts = db.query(Account).filter(
            and_(
                Account.id.in_(to_account_ids),
                Account.budget_id == budget_id,
                Account.deleted_at.is_(None),
            )
        ).all()
        if len(to_accounts) != len(to_account_ids):
            return None

    # Convert account IDs to strings for JSONB storage
    from_account_ids_json = [str(aid) for aid in from_account_ids] if from_account_ids else None
    to_account_ids_json = [str(aid) for aid in to_account_ids] if to_account_ids else None

    budget_post = BudgetPost(
        budget_id=budget_id,
        category_id=category_id,
        name=name,
        type=post_type,
        amount_min=amount_min,
        amount_max=amount_max,
        from_account_ids=from_account_ids_json,
        to_account_ids=to_account_ids_json,
        recurrence_pattern=recurrence_pattern,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(budget_post)
    db.commit()
    db.refresh(budget_post)

    return budget_post


def get_budget_posts(
    db: Session,
    budget_id: uuid.UUID,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[BudgetPost], str | None]:
    """
    Get paginated list of budget posts for a budget.

    Args:
        db: Database session
        budget_id: Budget UUID
        limit: Maximum number of items to return
        cursor: Pagination cursor (optional)

    Returns:
        Tuple of (list of budget posts, next cursor or None)
    """
    query = db.query(BudgetPost).filter(
        and_(
            BudgetPost.budget_id == budget_id,
            BudgetPost.deleted_at.is_(None),
        )
    )

    # Apply cursor pagination
    if cursor:
        try:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.filter(
                or_(
                    BudgetPost.created_at < cursor_created_at,
                    and_(
                        BudgetPost.created_at == cursor_created_at,
                        BudgetPost.id < cursor_id,
                    ),
                )
            )
        except ValueError:
            # Invalid cursor - ignore and start from beginning
            pass

    # Order by created_at DESC, id DESC for consistent pagination
    query = query.order_by(BudgetPost.created_at.desc(), BudgetPost.id.desc())

    # Fetch limit + 1 to determine if there are more items
    posts = query.limit(limit + 1).all()

    # Determine next cursor
    next_cursor = None
    if len(posts) > limit:
        last_post = posts[limit - 1]
        next_cursor = encode_cursor(last_post.created_at, last_post.id)
        posts = posts[:limit]

    return posts, next_cursor


def get_budget_post_by_id(
    db: Session,
    post_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> BudgetPost | None:
    """
    Get a single budget post by ID.

    Args:
        db: Database session
        post_id: Budget post UUID
        budget_id: Budget UUID (for authorization check)

    Returns:
        BudgetPost instance or None if not found
    """
    return db.query(BudgetPost).filter(
        and_(
            BudgetPost.id == post_id,
            BudgetPost.budget_id == budget_id,
            BudgetPost.deleted_at.is_(None),
        )
    ).first()


def update_budget_post(
    db: Session,
    post_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    name: str | None = None,
    post_type: BudgetPostType | None = None,
    amount_min: int | None = None,
    amount_max: int | None = None,
    from_account_ids: list[uuid.UUID] | None = None,
    to_account_ids: list[uuid.UUID] | None = None,
    recurrence_pattern: dict | None = None,
) -> BudgetPost | None:
    """
    Update a budget post.

    Args:
        db: Database session
        post_id: Budget post UUID
        budget_id: Budget UUID (for authorization check)
        user_id: User ID performing the update
        category_id: New category UUID (optional)
        name: New name (optional)
        post_type: New type (optional)
        amount_min: New minimum amount (optional)
        amount_max: New maximum amount (optional)
        from_account_ids: New source account IDs (optional)
        to_account_ids: New destination account IDs (optional)
        recurrence_pattern: New recurrence pattern (optional)

    Returns:
        Updated BudgetPost instance, or None if not found or validation fails
    """
    budget_post = get_budget_post_by_id(db, post_id, budget_id)
    if not budget_post:
        return None

    # Verify new category belongs to the same budget if provided
    if category_id is not None:
        category = db.query(Category).filter(
            and_(
                Category.id == category_id,
                Category.budget_id == budget_id,
                Category.deleted_at.is_(None),
            )
        ).first()
        if not category:
            return None
        budget_post.category_id = category_id

    # Verify all from_account_ids belong to the budget if provided
    if from_account_ids is not None:
        if from_account_ids:  # Non-empty list
            from_accounts = db.query(Account).filter(
                and_(
                    Account.id.in_(from_account_ids),
                    Account.budget_id == budget_id,
                    Account.deleted_at.is_(None),
                )
            ).all()
            if len(from_accounts) != len(from_account_ids):
                return None
            budget_post.from_account_ids = [str(aid) for aid in from_account_ids]
        else:  # Empty list
            budget_post.from_account_ids = None

    # Verify all to_account_ids belong to the budget if provided
    if to_account_ids is not None:
        if to_account_ids:  # Non-empty list
            to_accounts = db.query(Account).filter(
                and_(
                    Account.id.in_(to_account_ids),
                    Account.budget_id == budget_id,
                    Account.deleted_at.is_(None),
                )
            ).all()
            if len(to_accounts) != len(to_account_ids):
                return None
            budget_post.to_account_ids = [str(aid) for aid in to_account_ids]
        else:  # Empty list
            budget_post.to_account_ids = None

    # Update other fields if provided
    if name is not None:
        budget_post.name = name
    if post_type is not None:
        budget_post.type = post_type
    if amount_min is not None:
        budget_post.amount_min = amount_min
    if amount_max is not None:
        budget_post.amount_max = amount_max
    if recurrence_pattern is not None:
        budget_post.recurrence_pattern = recurrence_pattern

    budget_post.updated_by = user_id
    budget_post.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(budget_post)

    return budget_post


def soft_delete_budget_post(
    db: Session,
    post_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> bool:
    """
    Soft delete a budget post.

    Args:
        db: Database session
        post_id: Budget post UUID
        budget_id: Budget UUID (for authorization check)

    Returns:
        True if deleted, False if not found
    """
    budget_post = get_budget_post_by_id(db, post_id, budget_id)
    if not budget_post:
        return False

    budget_post.deleted_at = datetime.now(UTC)
    db.commit()

    return True
