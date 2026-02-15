"""Budget post service layer for business logic."""

import base64
import json
import uuid
from datetime import datetime, UTC, date, timedelta
from calendar import monthrange

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection, CounterpartyType
from api.models.amount_pattern import AmountPattern
from api.models.category import Category
from api.models.account import Account, AccountPurpose
from api.models.archived_budget_post import ArchivedBudgetPost
from api.models.amount_occurrence import AmountOccurrence
from api.schemas.budget_post import RecurrenceType, RelativePosition
from api.services.category_service import get_root_category
from api.utils.bank_days import adjust_to_bank_day, nth_bank_day_in_month


class BudgetPostValidationError(Exception):
    """Raised when budget post business rule validation fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BudgetPostConflictError(Exception):
    """Raised when UNIQUE constraint would be violated."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# NOTE: Period derivation and past-date validation removed as active budget posts no longer have periods


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


# NOTE: _validate_direction removed - validation logic changes with new model structure


def _validate_amount_pattern_accounts(
    db: Session,
    budget_id: uuid.UUID,
    direction: BudgetPostDirection,
    counterparty_type: CounterpartyType | None,
    amount_patterns: list[dict],
) -> None:
    """
    Validate account_ids on amount patterns based on direction and counterparty_type.

    Args:
        db: Database session
        budget_id: Budget UUID
        direction: Budget post direction
        counterparty_type: Counterparty type (for income/expense)
        amount_patterns: List of amount pattern dicts

    Raises:
        BudgetPostValidationError: If validation fails
    """
    for pattern_data in amount_patterns:
        pattern_account_ids = pattern_data.get("account_ids")

        if direction in (BudgetPostDirection.INCOME, BudgetPostDirection.EXPENSE):
            if counterparty_type == CounterpartyType.EXTERNAL:
                # Must have 1+ NORMAL accounts
                if not pattern_account_ids or len(pattern_account_ids) == 0:
                    raise BudgetPostValidationError(
                        "Amount patterns for income/expense with EXTERNAL counterparty must specify at least one account_id"
                    )

                # Verify all accounts are NORMAL and belong to budget
                for acc_id in pattern_account_ids:
                    try:
                        acc_uuid = uuid.UUID(acc_id)
                    except (ValueError, TypeError):
                        raise BudgetPostValidationError(
                            f"Invalid account_id format: {acc_id}"
                        )

                    account = db.query(Account).filter(
                        and_(
                            Account.id == acc_uuid,
                            Account.budget_id == budget_id,
                            Account.deleted_at.is_(None),
                        )
                    ).first()

                    if not account:
                        raise BudgetPostValidationError(
                            f"Account {acc_id} not found or does not belong to this budget"
                        )

                    if account.purpose != AccountPurpose.NORMAL:
                        raise BudgetPostValidationError(
                            f"Account {acc_id} must be a NORMAL account for amount patterns"
                        )

            elif counterparty_type == CounterpartyType.ACCOUNT:
                # Must have exactly 1 NORMAL account
                if not pattern_account_ids or len(pattern_account_ids) != 1:
                    raise BudgetPostValidationError(
                        "Amount patterns for income/expense with ACCOUNT counterparty must specify exactly one account_id"
                    )

                # Verify the account is NORMAL and belongs to budget
                try:
                    acc_uuid = uuid.UUID(pattern_account_ids[0])
                except (ValueError, TypeError):
                    raise BudgetPostValidationError(
                        f"Invalid account_id format: {pattern_account_ids[0]}"
                    )

                account = db.query(Account).filter(
                    and_(
                        Account.id == acc_uuid,
                        Account.budget_id == budget_id,
                        Account.deleted_at.is_(None),
                    )
                ).first()

                if not account:
                    raise BudgetPostValidationError(
                        f"Account {pattern_account_ids[0]} not found or does not belong to this budget"
                    )

                if account.purpose != AccountPurpose.NORMAL:
                    raise BudgetPostValidationError(
                        f"Account {pattern_account_ids[0]} must be a NORMAL account for amount patterns"
                    )

        elif direction == BudgetPostDirection.TRANSFER:
            # account_ids must be null or empty for transfers
            if pattern_account_ids and len(pattern_account_ids) > 0:
                raise BudgetPostValidationError(
                    "Amount patterns for transfer budget posts cannot have account_ids"
                )


def create_budget_post(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    direction: BudgetPostDirection,
    post_type: BudgetPostType,
    category_id: uuid.UUID | None = None,
    accumulate: bool = False,
    counterparty_type: CounterpartyType | None = None,
    counterparty_account_id: uuid.UUID | None = None,
    transfer_from_account_id: uuid.UUID | None = None,
    transfer_to_account_id: uuid.UUID | None = None,
    amount_patterns: list[dict] | None = None,
) -> BudgetPost | None:
    """
    Create a new budget post.

    Args:
        db: Database session
        budget_id: Budget UUID (must belong to user)
        user_id: User ID creating the post
        direction: Direction (income/expense/transfer)
        post_type: Type of budget post (fixed/ceiling)
        category_id: Category UUID (required for income/expense, null for transfer)
        accumulate: Whether to accumulate unused amounts (ceiling only)
        counterparty_type: Type of counterparty (external/account, null for transfer)
        counterparty_account_id: Counterparty account UUID (if counterparty_type=account)
        transfer_from_account_id: Transfer from account UUID (for transfer)
        transfer_to_account_id: Transfer to account UUID (for transfer)
        amount_patterns: List of amount pattern dicts (required)

    Returns:
        Created BudgetPost instance, or None if validation fails
    """
    # Verify category belongs to the same budget (if provided)
    if category_id:
        category = db.query(Category).filter(
            and_(
                Category.id == category_id,
                Category.budget_id == budget_id,
                Category.deleted_at.is_(None),
            )
        ).first()

        if not category:
            return None

    # Direction-based validation
    if direction in (BudgetPostDirection.INCOME, BudgetPostDirection.EXPENSE):
        # a) Income/Expense validation
        if not category_id:
            raise BudgetPostValidationError(
                f"{direction.value} budget posts require a category"
            )

        if not counterparty_type:
            raise BudgetPostValidationError(
                f"{direction.value} budget posts require a counterparty_type"
            )

        # Counterparty account validation
        if counterparty_type == CounterpartyType.ACCOUNT:
            if not counterparty_account_id:
                raise BudgetPostValidationError(
                    "counterparty_account_id is required when counterparty_type is ACCOUNT"
                )

            # Verify account exists, belongs to budget, and has correct purpose
            counterparty_account = db.query(Account).filter(
                and_(
                    Account.id == counterparty_account_id,
                    Account.budget_id == budget_id,
                    Account.deleted_at.is_(None),
                )
            ).first()

            if not counterparty_account:
                return None

            if counterparty_account.purpose not in (AccountPurpose.SAVINGS, AccountPurpose.LOAN):
                raise BudgetPostValidationError(
                    "Counterparty account must have purpose SAVINGS or LOAN"
                )

        elif counterparty_type == CounterpartyType.EXTERNAL:
            if counterparty_account_id:
                raise BudgetPostValidationError(
                    "counterparty_account_id must be null when counterparty_type is EXTERNAL"
                )

        # Transfer fields must be null for income/expense
        if transfer_from_account_id or transfer_to_account_id:
            raise BudgetPostValidationError(
                f"{direction.value} budget posts cannot have transfer accounts"
            )

        # Category-direction validation
        if category_id:
            root_category = get_root_category(db, category)
            if not root_category:
                raise BudgetPostValidationError(
                    "Category must belong to a root category tree"
                )

            # Income posts need "Indtægt" root, expense posts need "Udgift" root
            expected_root = "Indtægt" if direction == BudgetPostDirection.INCOME else "Udgift"
            if root_category.name != expected_root:
                raise BudgetPostValidationError(
                    f"{direction.value.capitalize()} budget posts must use categories under '{expected_root}' root"
                )

    elif direction == BudgetPostDirection.TRANSFER:
        # b) Transfer validation
        if category_id:
            raise BudgetPostValidationError(
                "Transfer budget posts cannot have a category"
            )

        if counterparty_type:
            raise BudgetPostValidationError(
                "Transfer budget posts cannot have a counterparty_type"
            )

        if counterparty_account_id:
            raise BudgetPostValidationError(
                "Transfer budget posts cannot have a counterparty_account_id"
            )

        if not transfer_from_account_id:
            raise BudgetPostValidationError(
                "Transfer budget posts require transfer_from_account_id"
            )

        if not transfer_to_account_id:
            raise BudgetPostValidationError(
                "Transfer budget posts require transfer_to_account_id"
            )

        if transfer_from_account_id == transfer_to_account_id:
            raise BudgetPostValidationError(
                "transfer_from_account_id and transfer_to_account_id must be different"
            )

        # Verify both accounts exist, belong to budget, and are NORMAL
        from_account = db.query(Account).filter(
            and_(
                Account.id == transfer_from_account_id,
                Account.budget_id == budget_id,
                Account.deleted_at.is_(None),
            )
        ).first()

        if not from_account:
            return None

        if from_account.purpose != AccountPurpose.NORMAL:
            raise BudgetPostValidationError(
                "transfer_from_account_id must reference a NORMAL account"
            )

        to_account = db.query(Account).filter(
            and_(
                Account.id == transfer_to_account_id,
                Account.budget_id == budget_id,
                Account.deleted_at.is_(None),
            )
        ).first()

        if not to_account:
            return None

        if to_account.purpose != AccountPurpose.NORMAL:
            raise BudgetPostValidationError(
                "transfer_to_account_id must reference a NORMAL account"
            )

    # d) Accumulate validation
    if accumulate and post_type != BudgetPostType.CEILING:
        raise BudgetPostValidationError(
            "accumulate can only be true for CEILING type budget posts"
        )

    # c) Amount pattern account_ids validation
    if amount_patterns:
        _validate_amount_pattern_accounts(
            db=db,
            budget_id=budget_id,
            direction=direction,
            counterparty_type=counterparty_type,
            amount_patterns=amount_patterns,
        )

    budget_post = BudgetPost(
        budget_id=budget_id,
        direction=direction,
        category_id=category_id,
        type=post_type,
        accumulate=accumulate,
        counterparty_type=counterparty_type,
        counterparty_account_id=counterparty_account_id,
        transfer_from_account_id=transfer_from_account_id,
        transfer_to_account_id=transfer_to_account_id,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(budget_post)

    try:
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
                    account_ids=pattern_data.get("account_ids"),
                )
                db.add(amount_pattern)

        db.commit()
    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError) and "uq_budget_post_category" in str(e.orig):
            raise BudgetPostConflictError(
                f"Budget post already exists for this category"
            )
        raise

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
    ).options(joinedload(BudgetPost.category))

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
    ).options(joinedload(BudgetPost.category)).first()


def update_budget_post(
    db: Session,
    post_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    post_type: BudgetPostType | None = None,
    accumulate: bool | None = None,
    counterparty_type: CounterpartyType | None = None,
    counterparty_account_id: uuid.UUID | None = None,
    transfer_from_account_id: uuid.UUID | None = None,
    transfer_to_account_id: uuid.UUID | None = None,
    amount_patterns: list[dict] | None = None,
) -> BudgetPost | None:
    """
    Update a budget post.

    Args:
        db: Database session
        post_id: Budget post UUID
        budget_id: Budget UUID (for authorization check)
        user_id: User ID performing the update
        post_type: New type (optional)
        accumulate: New accumulate flag (optional)
        counterparty_type: New counterparty type (optional)
        counterparty_account_id: New counterparty account ID (optional)
        transfer_from_account_id: New transfer from account (optional)
        transfer_to_account_id: New transfer to account (optional)
        amount_patterns: New amount patterns (replaces all existing, optional)

    Returns:
        Updated BudgetPost instance, or None if not found or validation fails
    """
    budget_post = get_budget_post_by_id(db, post_id, budget_id)
    if not budget_post:
        return None

    # Get current direction (immutable)
    direction = budget_post.direction

    # Validate counterparty_type changes if provided
    if counterparty_type is not None:
        if direction == BudgetPostDirection.TRANSFER:
            raise BudgetPostValidationError(
                "Transfer budget posts cannot have a counterparty_type"
            )

        # If changing counterparty_type, validate the new value
        if counterparty_type == CounterpartyType.ACCOUNT:
            if counterparty_account_id is not None:
                # Verify account exists, belongs to budget, and has correct purpose
                counterparty_account = db.query(Account).filter(
                    and_(
                        Account.id == counterparty_account_id,
                        Account.budget_id == budget_id,
                        Account.deleted_at.is_(None),
                    )
                ).first()

                if not counterparty_account:
                    return None

                if counterparty_account.purpose not in (AccountPurpose.SAVINGS, AccountPurpose.LOAN):
                    raise BudgetPostValidationError(
                        "Counterparty account must have purpose SAVINGS or LOAN"
                    )

        elif counterparty_type == CounterpartyType.EXTERNAL:
            # counterparty_account_id should be null for EXTERNAL
            pass

    # Validate transfer account changes
    if transfer_from_account_id is not None or transfer_to_account_id is not None:
        if direction != BudgetPostDirection.TRANSFER:
            raise BudgetPostValidationError(
                "Only transfer budget posts can have transfer accounts"
            )

        # Use current values if not being updated
        new_from = transfer_from_account_id if transfer_from_account_id is not None else budget_post.transfer_from_account_id
        new_to = transfer_to_account_id if transfer_to_account_id is not None else budget_post.transfer_to_account_id

        if new_from and new_to and new_from == new_to:
            raise BudgetPostValidationError(
                "transfer_from_account_id and transfer_to_account_id must be different"
            )

        # Validate the accounts if being set
        if transfer_from_account_id is not None:
            from_account = db.query(Account).filter(
                and_(
                    Account.id == transfer_from_account_id,
                    Account.budget_id == budget_id,
                    Account.deleted_at.is_(None),
                )
            ).first()

            if not from_account:
                return None

            if from_account.purpose != AccountPurpose.NORMAL:
                raise BudgetPostValidationError(
                    "transfer_from_account_id must reference a NORMAL account"
                )

        if transfer_to_account_id is not None:
            to_account = db.query(Account).filter(
                and_(
                    Account.id == transfer_to_account_id,
                    Account.budget_id == budget_id,
                    Account.deleted_at.is_(None),
                )
            ).first()

            if not to_account:
                return None

            if to_account.purpose != AccountPurpose.NORMAL:
                raise BudgetPostValidationError(
                    "transfer_to_account_id must reference a NORMAL account"
                )

    # Validate accumulate changes
    if accumulate is not None:
        new_type = post_type if post_type is not None else budget_post.type
        if accumulate and new_type != BudgetPostType.CEILING:
            raise BudgetPostValidationError(
                "accumulate can only be true for CEILING type budget posts"
            )

    # Update fields if provided
    if post_type is not None:
        budget_post.type = post_type

    if accumulate is not None:
        budget_post.accumulate = accumulate

    if counterparty_type is not None:
        budget_post.counterparty_type = counterparty_type
        # Clear counterparty_account_id when changing to EXTERNAL
        if counterparty_type == CounterpartyType.EXTERNAL:
            budget_post.counterparty_account_id = None

    if counterparty_account_id is not None:
        budget_post.counterparty_account_id = counterparty_account_id

    if transfer_from_account_id is not None:
        budget_post.transfer_from_account_id = transfer_from_account_id

    if transfer_to_account_id is not None:
        budget_post.transfer_to_account_id = transfer_to_account_id

    budget_post.updated_by = user_id
    budget_post.updated_at = datetime.now(UTC)

    # Handle amount_patterns replacement if provided
    if amount_patterns is not None:
        # Determine counterparty_type for validation (use updated or existing)
        effective_counterparty_type = counterparty_type if counterparty_type is not None else budget_post.counterparty_type

        # Validate account_ids on new patterns
        _validate_amount_pattern_accounts(
            db=db,
            budget_id=budget_id,
            direction=direction,
            counterparty_type=effective_counterparty_type,
            amount_patterns=amount_patterns,
        )

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
                account_ids=pattern_data.get("account_ids"),
            )
            db.add(amount_pattern)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError) and "uq_budget_post_category" in str(e.orig):
            raise BudgetPostConflictError(
                f"Budget post already exists for this category"
            )
        raise

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


def _get_nth_weekday(year: int, month: int, weekday: int, position: str) -> date | None:
    """
    Get the nth occurrence of a weekday in a month.

    Args:
        year: Year
        month: Month (1-12)
        weekday: Weekday (0=Monday, 6=Sunday)
        position: "first", "second", "third", "fourth", or "last"

    Returns:
        Date of the nth weekday, or None if it doesn't exist in that month
    """
    if position == "last":
        # Start from the last day and work backwards
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)

    # For first/second/third/fourth: find the Nth occurrence
    position_map = {"first": 1, "second": 2, "third": 3, "fourth": 4}
    n = position_map.get(position)
    if n is None:
        return None

    # Find first occurrence of the weekday in the month
    first_day = date(year, month, 1)
    days_ahead = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=days_ahead)

    # Add (n-1) weeks to get the nth occurrence
    result = first_occurrence + timedelta(weeks=n - 1)

    # Check it's still in the same month
    if result.month != month:
        return None

    return result


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
            recurrence_type = pattern.recurrence_pattern.get("type")
            if recurrence_type == RecurrenceType.ONCE.value:
                # once: start_date IS the occurrence date
                if effective_start <= pattern_start <= effective_end:
                    bank_day_adj = pattern.recurrence_pattern.get("bank_day_adjustment", "none")
                    keep_in_month = pattern.recurrence_pattern.get("bank_day_keep_in_month", True)
                    occ_date = adjust_to_bank_day(pattern_start, bank_day_adj, keep_in_month=keep_in_month) if bank_day_adj != "none" else pattern_start
                    if occ_date <= effective_end:
                        all_occurrences.append((occ_date, pattern.amount))
            elif recurrence_type == RecurrenceType.PERIOD_ONCE.value:
                # period_once: start_date year+month determines the occurrence period
                occ_date = date(pattern_start.year, pattern_start.month, 1)
                # Check if occurrence is within the requested query range
                if start_date <= occ_date <= end_date:
                    all_occurrences.append((occ_date, pattern.amount))
            else:
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
    bank_day_adj = pattern.get("bank_day_adjustment", "none")
    keep_in_month = pattern.get("bank_day_keep_in_month", True)

    # Date-based recurrence types
    if recurrence_type == RecurrenceType.DAILY.value:
        # Every N days starting from start_date
        current = start_date
        while current <= end_date:
            if bank_day_adj != "none":
                adjusted = adjust_to_bank_day(current, bank_day_adj, keep_in_month=keep_in_month)
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
                if bank_day_adj != "none":
                    adjusted = adjust_to_bank_day(current, bank_day_adj, keep_in_month=keep_in_month)
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
                    if bank_day_adj != "none":
                        adjusted = adjust_to_bank_day(occurrence, bank_day_adj, keep_in_month=keep_in_month)
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
        # Every N months on nth weekday (first/second/third/fourth/last)
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
                    if bank_day_adj != "none":
                        adjusted = adjust_to_bank_day(occurrence, bank_day_adj, keep_in_month=keep_in_month)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

                # Move to next interval
                current_month += interval
                while current_month > 12:
                    current_month -= 12
                    current_year += 1

    elif recurrence_type == RecurrenceType.MONTHLY_BANK_DAY.value:
        # Every N months on nth bank day (from start or end)
        bank_day_number = pattern.get("bank_day_number")
        bank_day_from_end = pattern.get("bank_day_from_end")

        if bank_day_number is not None and bank_day_from_end is not None:
            current_year = start_date.year
            current_month = start_date.month

            while True:
                # Check termination before calling nth_bank_day_in_month
                if date(current_year, current_month, 1) > end_date:
                    break

                occurrence = nth_bank_day_in_month(current_year, current_month, bank_day_number, bank_day_from_end)

                # Skip if month doesn't have enough bank days (don't break - try next month)
                if occurrence is None:
                    # Move to next interval
                    current_month += interval
                    while current_month > 12:
                        current_month -= 12
                        current_year += 1
                    continue

                if occurrence > end_date:
                    break

                if occurrence >= start_date:
                    # No bank_day_adjustment applied for bank day types
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
                    if bank_day_adj != "none":
                        adjusted = adjust_to_bank_day(occurrence, bank_day_adj, keep_in_month=keep_in_month)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

                current_year += interval

    elif recurrence_type == RecurrenceType.YEARLY_BANK_DAY.value:
        # Every N years in specific month on nth bank day
        month = pattern.get("month")
        bank_day_number = pattern.get("bank_day_number")
        bank_day_from_end = pattern.get("bank_day_from_end")

        if month is not None and bank_day_number is not None and bank_day_from_end is not None:
            current_year = start_date.year

            while True:
                # Check termination before calling nth_bank_day_in_month
                if date(current_year, month, 1) > end_date:
                    break

                occurrence = nth_bank_day_in_month(current_year, month, bank_day_number, bank_day_from_end)

                # Skip if month doesn't have enough bank days (don't break - try next year)
                if occurrence is None:
                    current_year += interval
                    continue

                if occurrence > end_date:
                    break

                if occurrence >= start_date:
                    # No bank_day_adjustment applied for bank day types
                    occurrences.append(occurrence)

                current_year += interval

    # Period-based recurrence types
    if recurrence_type == RecurrenceType.PERIOD_MONTHLY.value:
        # Every N months from start
        current_year = start_date.year
        current_month = start_date.month
        while True:
            occurrence = date(current_year, current_month, 1)
            if occurrence > end_date:
                break
            if occurrence >= start_date:
                if bank_day_adj != "none":
                    adjusted = adjust_to_bank_day(occurrence, bank_day_adj, keep_in_month=keep_in_month)
                    if adjusted <= end_date and adjusted not in occurrences:
                        occurrences.append(adjusted)
                else:
                    occurrences.append(occurrence)
            # Advance by interval months
            current_month += interval
            while current_month > 12:
                current_month -= 12
                current_year += 1

    if recurrence_type == RecurrenceType.PERIOD_YEARLY.value:
        # Every N years in specific months
        months = pattern.get("months", [])
        current_year = start_date.year

        while current_year <= end_date.year:
            for month in months:
                occurrence = date(current_year, month, 1)

                if occurrence > end_date:
                    break

                if occurrence >= start_date:
                    if bank_day_adj != "none":
                        adjusted = adjust_to_bank_day(occurrence, bank_day_adj, keep_in_month=keep_in_month)
                        if adjusted <= end_date and adjusted not in occurrences:
                            occurrences.append(adjusted)
                    else:
                        occurrences.append(occurrence)

            current_year += interval

    # Remove duplicates and sort
    occurrences = sorted(set(occurrences))

    return occurrences


def create_archived_budget_post(
    db: Session,
    budget_id: uuid.UUID,
    budget_post: BudgetPost,
    period_year: int,
    period_month: int,
    user_id: uuid.UUID,
) -> ArchivedBudgetPost:
    """
    Create an archived budget post snapshot for a specific period.

    Expands the active budget post's amount patterns into concrete
    amount occurrences for the given period month.

    Args:
        db: Database session
        budget_id: Budget UUID
        budget_post: Active budget post to archive
        period_year: Year of the period
        period_month: Month of the period (1-12)
        user_id: User ID creating the archive

    Returns:
        Created ArchivedBudgetPost with amount occurrences
    """
    # Create the archived budget post
    archived_post = ArchivedBudgetPost(
        budget_id=budget_id,
        budget_post_id=budget_post.id,
        period_year=period_year,
        period_month=period_month,
        direction=budget_post.direction,
        category_id=budget_post.category_id,
        type=budget_post.type,
        created_by=user_id,
    )

    db.add(archived_post)
    db.flush()  # Get the archived_post.id

    # Calculate period date range (first to last day of the month)
    first_day = date(period_year, period_month, 1)
    last_day_num = monthrange(period_year, period_month)[1]
    last_day = date(period_year, period_month, last_day_num)

    # Expand amount patterns for the period
    occurrence_tuples = expand_amount_patterns_to_occurrences(
        budget_post,
        first_day,
        last_day,
    )

    # Create amount occurrences
    for occ_date, amount in occurrence_tuples:
        occurrence = AmountOccurrence(
            archived_budget_post_id=archived_post.id,
            date=occ_date,
            amount=amount,
        )
        db.add(occurrence)

    db.commit()
    db.refresh(archived_post)

    return archived_post


def get_archived_budget_posts(
    db: Session,
    budget_id: uuid.UUID,
    period_year: int | None = None,
    period_month: int | None = None,
) -> list[ArchivedBudgetPost]:
    """
    Get archived budget posts for a budget, optionally filtered by period.

    Args:
        db: Database session
        budget_id: Budget UUID
        period_year: Optional year filter
        period_month: Optional month filter (1-12)

    Returns:
        List of ArchivedBudgetPost instances
    """
    query = db.query(ArchivedBudgetPost).filter(
        ArchivedBudgetPost.budget_id == budget_id
    ).options(
        joinedload(ArchivedBudgetPost.category),
        joinedload(ArchivedBudgetPost.amount_occurrences),
    )

    if period_year is not None:
        query = query.filter(ArchivedBudgetPost.period_year == period_year)

    if period_month is not None:
        query = query.filter(ArchivedBudgetPost.period_month == period_month)

    # Order by period descending
    query = query.order_by(
        ArchivedBudgetPost.period_year.desc(),
        ArchivedBudgetPost.period_month.desc(),
    )

    return query.all()


def get_archived_budget_post_by_id(
    db: Session,
    archived_post_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> ArchivedBudgetPost | None:
    """
    Get a single archived budget post by ID.

    Args:
        db: Database session
        archived_post_id: Archived budget post UUID
        budget_id: Budget UUID (for authorization check)

    Returns:
        ArchivedBudgetPost instance or None if not found
    """
    return db.query(ArchivedBudgetPost).filter(
        and_(
            ArchivedBudgetPost.id == archived_post_id,
            ArchivedBudgetPost.budget_id == budget_id,
        )
    ).options(
        joinedload(ArchivedBudgetPost.category),
        joinedload(ArchivedBudgetPost.amount_occurrences),
    ).first()
