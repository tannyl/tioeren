"""Budget post service layer for business logic."""

import base64
import json
import uuid
from datetime import datetime, UTC, date, timedelta
from calendar import monthrange

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.models.budget_post import BudgetPost, BudgetPostType
from api.models.amount_pattern import AmountPattern
from api.models.category import Category
from api.models.account import Account
from api.schemas.budget_post import RecurrenceType, RelativePosition


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
    from_account_ids: list[uuid.UUID] | None = None,
    to_account_ids: list[uuid.UUID] | None = None,
    amount_patterns: list[dict] | None = None,
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
        from_account_ids: List of source account UUIDs (optional)
        to_account_ids: List of destination account UUIDs (optional)
        amount_patterns: List of amount pattern dicts (required)

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
        from_account_ids=from_account_ids_json,
        to_account_ids=to_account_ids_json,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(budget_post)
    db.flush()  # Get the budget_post.id without committing

    # Create amount patterns (required)
    if amount_patterns:
        for pattern_data in amount_patterns:
            amount_pattern = AmountPattern(
                budget_post_id=budget_post.id,
                amount=pattern_data["amount"],
                start_date=date.fromisoformat(pattern_data["start_date"]),
                end_date=date.fromisoformat(pattern_data["end_date"]) if pattern_data.get("end_date") else None,
                recurrence_pattern=pattern_data.get("recurrence_pattern"),
            )
            db.add(amount_pattern)

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
    from_account_ids: list[uuid.UUID] | None = None,
    to_account_ids: list[uuid.UUID] | None = None,
    amount_patterns: list[dict] | None = None,
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
        from_account_ids: New source account IDs (optional)
        to_account_ids: New destination account IDs (optional)
        amount_patterns: New amount patterns (replaces all existing, optional)

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

    budget_post.updated_by = user_id
    budget_post.updated_at = datetime.now(UTC)

    # Handle amount_patterns replacement if provided
    if amount_patterns is not None:
        # Delete all existing patterns
        db.query(AmountPattern).filter(
            AmountPattern.budget_post_id == post_id
        ).delete()

        # Create new patterns
        for pattern_data in amount_patterns:
            amount_pattern = AmountPattern(
                budget_post_id=post_id,
                amount=pattern_data["amount"],
                start_date=date.fromisoformat(pattern_data["start_date"]),
                end_date=date.fromisoformat(pattern_data["end_date"]) if pattern_data.get("end_date") else None,
                recurrence_pattern=pattern_data.get("recurrence_pattern"),
            )
            db.add(amount_pattern)

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


def _postpone_weekend(d: date) -> date:
    """
    Postpone date to next Monday if it falls on weekend.

    Args:
        d: Date to check

    Returns:
        Original date if weekday, or next Monday if weekend
    """
    # 5 = Saturday, 6 = Sunday
    if d.weekday() == 5:  # Saturday
        return d + timedelta(days=2)
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _get_nth_weekday(year: int, month: int, weekday: int, position: str) -> date | None:
    """
    Get the first or last occurrence of a weekday in a month.

    Args:
        year: Year
        month: Month (1-12)
        weekday: Weekday (0=Monday, 6=Sunday)
        position: "first" or "last"

    Returns:
        Date of the nth weekday, or None if not found
    """
    if position == "first":
        # Start from the 1st and find first occurrence
        first_day = date(year, month, 1)
        days_ahead = (weekday - first_day.weekday()) % 7
        return first_day + timedelta(days=days_ahead)
    elif position == "last":
        # Start from the last day and work backwards
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)
    return None


def expand_amount_patterns_to_occurrences(
    budget_post: BudgetPost,
    start_date: date,
    end_date: date,
) -> list[tuple[date, int]]:
    """
    Expand all active amount patterns into concrete occurrence dates with amounts.

    Args:
        budget_post: Budget post with amount patterns
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of (date, amount) tuples within the date range, sorted chronologically
    """
    all_occurrences: list[tuple[date, int]] = []

    # Expand all amount patterns
    for pattern in budget_post.amount_patterns:
        # Check if pattern is active in the requested date range
        pattern_start = pattern.start_date
        pattern_end = pattern.end_date if pattern.end_date else date.max

        # Skip patterns that don't overlap with the requested range
        if pattern_end < start_date or pattern_start > end_date:
            continue

        # Determine the effective date range for this pattern
        effective_start = max(start_date, pattern_start)
        effective_end = min(end_date, pattern_end)

        # Expand this pattern's recurrence within its effective date range
        if pattern.recurrence_pattern:
            occurrence_dates = _expand_recurrence_pattern(
                pattern.recurrence_pattern,
                effective_start,
                effective_end,
            )
            # Add amount to each occurrence
            for occ_date in occurrence_dates:
                all_occurrences.append((occ_date, pattern.amount))

    # Sort by date
    all_occurrences.sort(key=lambda x: x[0])

    return all_occurrences


def expand_recurrence_to_occurrences(
    budget_post: BudgetPost,
    start_date: date,
    end_date: date,
) -> list[date]:
    """
    Expand recurrence pattern into concrete occurrence dates (legacy function).

    Args:
        budget_post: Budget post with recurrence pattern
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of occurrence dates within the date range, sorted chronologically
    """
    if not budget_post.recurrence_pattern:
        return []

    return _expand_recurrence_pattern(budget_post.recurrence_pattern, start_date, end_date)


def _expand_recurrence_pattern(
    pattern: dict,
    start_date: date,
    end_date: date,
) -> list[date]:
    """
    Expand a recurrence pattern dict into concrete occurrence dates.

    Args:
        pattern: Recurrence pattern dictionary
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of occurrence dates within the date range, sorted chronologically
    """
    recurrence_type = pattern.get("type")
    if not recurrence_type:
        return []

    occurrences: list[date] = []
    interval = pattern.get("interval", 1)
    postpone_weekend = pattern.get("postpone_weekend", False)

    # Date-based recurrence types
    if recurrence_type == RecurrenceType.ONCE.value:
        # Single occurrence on specific date
        occurrence_date_str = pattern.get("date")
        if occurrence_date_str:
            try:
                occurrence_date = date.fromisoformat(occurrence_date_str)
                if start_date <= occurrence_date <= end_date:
                    if postpone_weekend:
                        occurrence_date = _postpone_weekend(occurrence_date)
                    occurrences.append(occurrence_date)
            except ValueError:
                pass

    elif recurrence_type == RecurrenceType.DAILY.value:
        # Every N days starting from start_date
        current = start_date
        while current <= end_date:
            if postpone_weekend:
                adjusted = _postpone_weekend(current)
                if adjusted <= end_date and adjusted not in occurrences:
                    occurrences.append(adjusted)
            else:
                occurrences.append(current)
            current += timedelta(days=interval)

    elif recurrence_type == RecurrenceType.WEEKLY.value:
        # Every N weeks on specific weekday
        weekday = pattern.get("weekday")
        if weekday is not None:
            # Find first occurrence of the weekday on or after start_date
            days_ahead = (weekday - start_date.weekday()) % 7
            current = start_date + timedelta(days=days_ahead)

            while current <= end_date:
                if postpone_weekend:
                    adjusted = _postpone_weekend(current)
                    if adjusted <= end_date and adjusted not in occurrences:
                        occurrences.append(adjusted)
                else:
                    occurrences.append(current)
                current += timedelta(weeks=interval)

    elif recurrence_type == RecurrenceType.MONTHLY_FIXED.value:
        # Every N months on specific day of month
        day_of_month = pattern.get("day_of_month")
        if day_of_month is not None:
            # Start from the month containing start_date
            current_year = start_date.year
            current_month = start_date.month

            while True:
                # Get last day of current month
                last_day = monthrange(current_year, current_month)[1]
                # Use min to handle months with fewer days (e.g., Feb 31 -> Feb 28/29)
                actual_day = min(day_of_month, last_day)
                occurrence = date(current_year, current_month, actual_day)

                if occurrence > end_date:
                    break

                if occurrence >= start_date:
                    if postpone_weekend:
                        adjusted = _postpone_weekend(occurrence)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

                # Move to next interval
                current_month += interval
                while current_month > 12:
                    current_month -= 12
                    current_year += 1

    elif recurrence_type == RecurrenceType.MONTHLY_RELATIVE.value:
        # Every N months on first/last weekday
        weekday = pattern.get("weekday")
        relative_position = pattern.get("relative_position")

        if weekday is not None and relative_position is not None:
            current_year = start_date.year
            current_month = start_date.month

            while True:
                occurrence = _get_nth_weekday(current_year, current_month, weekday, relative_position)

                if occurrence is None or occurrence > end_date:
                    break

                if occurrence >= start_date:
                    if postpone_weekend:
                        adjusted = _postpone_weekend(occurrence)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

                # Move to next interval
                current_month += interval
                while current_month > 12:
                    current_month -= 12
                    current_year += 1

    elif recurrence_type == RecurrenceType.YEARLY.value:
        # Every N years in specific month
        month = pattern.get("month")
        day_of_month = pattern.get("day_of_month")
        weekday = pattern.get("weekday")
        relative_position = pattern.get("relative_position")

        if month is not None:
            current_year = start_date.year

            while True:
                if day_of_month is not None:
                    # Fixed day in the month
                    last_day = monthrange(current_year, month)[1]
                    actual_day = min(day_of_month, last_day)
                    occurrence = date(current_year, month, actual_day)
                elif weekday is not None and relative_position is not None:
                    # Relative weekday in the month
                    occurrence = _get_nth_weekday(current_year, month, weekday, relative_position)
                else:
                    break

                if occurrence is None or occurrence > end_date:
                    break

                if occurrence >= start_date:
                    if postpone_weekend:
                        adjusted = _postpone_weekend(occurrence)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

                current_year += interval

    # Period-based recurrence types
    elif recurrence_type == RecurrenceType.PERIOD_ONCE.value:
        # Occurs once in specific months (any year within range)
        months = pattern.get("months", [])

        for year in range(start_date.year, end_date.year + 1):
            for month in months:
                # Use the first day of the month as the occurrence
                occurrence = date(year, month, 1)

                if start_date <= occurrence <= end_date:
                    if postpone_weekend:
                        adjusted = _postpone_weekend(occurrence)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

    elif recurrence_type == RecurrenceType.PERIOD_YEARLY.value:
        # Every N years in specific months
        months = pattern.get("months", [])
        current_year = start_date.year

        while current_year <= end_date.year:
            for month in months:
                occurrence = date(current_year, month, 1)

                if occurrence > end_date:
                    break

                if occurrence >= start_date:
                    if postpone_weekend:
                        adjusted = _postpone_weekend(occurrence)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

            current_year += interval

    # Remove duplicates and sort
    occurrences = sorted(set(occurrences))

    return occurrences
