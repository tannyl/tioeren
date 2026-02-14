"""Transaction service layer for business logic."""

import base64
import json
import uuid
from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.models.transaction import Transaction, TransactionStatus
from api.models.account import Account
from api.models.transaction_allocation import TransactionAllocation
from api.models.amount_pattern import AmountPattern
from api.models.amount_occurrence import AmountOccurrence
from api.models.archived_budget_post import ArchivedBudgetPost


def encode_cursor(transaction_date: date, transaction_id: uuid.UUID) -> str:
    """
    Encode pagination cursor from date and id.

    Args:
        transaction_date: Transaction date
        transaction_id: Transaction UUID

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "date": transaction_date.isoformat(),
        "id": str(transaction_id),
    }
    cursor_json = json.dumps(cursor_data)
    return base64.urlsafe_b64encode(cursor_json.encode()).decode()


def decode_cursor(cursor: str) -> tuple[date, uuid.UUID]:
    """
    Decode pagination cursor to date and id.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (date, transaction_id)

    Raises:
        ValueError: If cursor is invalid
    """
    try:
        cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
        cursor_data = json.loads(cursor_json)
        transaction_date = date.fromisoformat(cursor_data["date"])
        transaction_id = uuid.UUID(cursor_data["id"])
        return transaction_date, transaction_id
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid cursor: {e}")


def get_budget_transactions(
    db: Session,
    budget_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
    status: TransactionStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[tuple[Transaction, str]], str | None]:
    """
    Get paginated list of transactions for a budget with filters.

    Args:
        db: Database session
        budget_id: Budget ID to get transactions for
        account_id: Optional account filter
        status: Optional status filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        limit: Maximum number of items to return
        cursor: Optional cursor for pagination

    Returns:
        Tuple of (list of (transaction, account_name) tuples, next cursor or None)
    """
    # Start with base query - join with accounts to filter by budget and get account name
    query = db.query(Transaction, Account.name).join(Account).filter(
        Account.budget_id == budget_id,
        Account.deleted_at.is_(None),
    )

    # Apply filters
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if status:
        query = query.filter(Transaction.status == status)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)

    # Apply cursor if provided
    if cursor:
        try:
            cursor_date, cursor_id = decode_cursor(cursor)
            # For descending order: (date < cursor_date) OR (date = cursor_date AND id < cursor_id)
            query = query.filter(
                or_(
                    Transaction.date < cursor_date,
                    and_(
                        Transaction.date == cursor_date,
                        Transaction.id < cursor_id,
                    ),
                )
            )
        except ValueError:
            # Invalid cursor, return empty result
            return [], None

    # Sort by date DESC, then id DESC for stable ordering
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())

    # Fetch limit + 1 to check if there are more items
    results = query.limit(limit + 1).all()

    # Determine next cursor
    next_cursor = None
    if len(results) > limit:
        last_transaction, _ = results[limit - 1]
        next_cursor = encode_cursor(last_transaction.date, last_transaction.id)
        results = results[:limit]

    return results, next_cursor


def create_transaction(
    db: Session,
    account_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    transaction_date: date,
    amount: int,
    description: str,
    is_internal_transfer: bool = False,
    counterpart_account_id: uuid.UUID | None = None,
) -> Transaction | None:
    """
    Create a new transaction, with optional internal transfer handling.

    Args:
        db: Database session
        account_id: Account ID for the transaction
        budget_id: Budget ID (for authorization check)
        user_id: User ID creating the transaction
        transaction_date: Date of the transaction
        amount: Amount in øre (positive = income, negative = expense)
        description: Transaction description
        is_internal_transfer: Whether this is an internal transfer
        counterpart_account_id: Counterpart account for internal transfer

    Returns:
        Created Transaction instance, or None if account not found/invalid
    """
    # Validate account belongs to budget
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.budget_id == budget_id,
        Account.deleted_at.is_(None),
    ).first()

    if not account:
        return None

    # If internal transfer, validate counterpart account
    if is_internal_transfer and counterpart_account_id:
        counterpart_account = db.query(Account).filter(
            Account.id == counterpart_account_id,
            Account.budget_id == budget_id,
            Account.deleted_at.is_(None),
        ).first()

        if not counterpart_account:
            return None

        # Create both transactions (linked)
        transaction1 = Transaction(
            account_id=account_id,
            date=transaction_date,
            amount=amount,
            description=description,
            status=TransactionStatus.CATEGORIZED,  # Internal transfers are auto-categorized
            is_internal_transfer=True,
            created_by=user_id,
            updated_by=user_id,
        )

        transaction2 = Transaction(
            account_id=counterpart_account_id,
            date=transaction_date,
            amount=-amount,  # Opposite amount
            description=description,
            status=TransactionStatus.CATEGORIZED,
            is_internal_transfer=True,
            created_by=user_id,
            updated_by=user_id,
        )

        # Add both and flush to get IDs
        db.add(transaction1)
        db.add(transaction2)
        db.flush()

        # Link them
        transaction1.counterpart_transaction_id = transaction2.id
        transaction2.counterpart_transaction_id = transaction1.id

        db.commit()
        db.refresh(transaction1)

        return transaction1
    else:
        # Create single transaction
        transaction = Transaction(
            account_id=account_id,
            date=transaction_date,
            amount=amount,
            description=description,
            status=TransactionStatus.UNCATEGORIZED,
            is_internal_transfer=False,
            created_by=user_id,
            updated_by=user_id,
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return transaction


def get_transaction_by_id(
    db: Session,
    transaction_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Transaction | None:
    """
    Get a single transaction by ID.

    Args:
        db: Database session
        transaction_id: Transaction ID to retrieve
        budget_id: Budget ID (for authorization check)

    Returns:
        Transaction if found and belongs to budget, None otherwise
    """
    return db.query(Transaction).join(Account).filter(
        Transaction.id == transaction_id,
        Account.budget_id == budget_id,
        Account.deleted_at.is_(None),
    ).first()


def update_transaction(
    db: Session,
    transaction_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    transaction_date: date | None = None,
    amount: int | None = None,
    description: str | None = None,
    status: TransactionStatus | None = None,
) -> Transaction | None:
    """
    Update a transaction.

    Args:
        db: Database session
        transaction_id: Transaction ID to update
        budget_id: Budget ID (for authorization check)
        user_id: User ID updating the transaction
        transaction_date: Optional new date
        amount: Optional new amount
        description: Optional new description
        status: Optional new status

    Returns:
        Updated Transaction if found and belongs to budget, None otherwise
    """
    transaction = get_transaction_by_id(db, transaction_id, budget_id)
    if not transaction:
        return None

    # Update fields if provided
    if transaction_date is not None:
        transaction.date = transaction_date
    if amount is not None:
        transaction.amount = amount
    if description is not None:
        transaction.description = description
    if status is not None:
        transaction.status = status

    transaction.updated_by = user_id

    db.commit()
    db.refresh(transaction)

    return transaction


def delete_transaction(
    db: Session,
    transaction_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> bool:
    """
    Hard delete a transaction. If internal transfer, delete both linked transactions.

    Args:
        db: Database session
        transaction_id: Transaction ID to delete
        budget_id: Budget ID (for authorization check)

    Returns:
        True if transaction was deleted, False if not found or not in budget
    """
    transaction = get_transaction_by_id(db, transaction_id, budget_id)
    if not transaction:
        return False

    # If internal transfer, also delete counterpart
    if transaction.is_internal_transfer and transaction.counterpart_transaction_id:
        counterpart = db.query(Transaction).filter(
            Transaction.id == transaction.counterpart_transaction_id
        ).first()

        # Break the circular reference before deletion
        if counterpart:
            transaction.counterpart_transaction_id = None
            counterpart.counterpart_transaction_id = None
            db.flush()

            # Now delete both
            db.delete(counterpart)
            db.delete(transaction)
        else:
            # Counterpart doesn't exist, just delete this one
            db.delete(transaction)
    else:
        # Not an internal transfer, just delete
        db.delete(transaction)

    db.commit()

    return True


def allocate_transaction(
    db: Session,
    transaction_id: uuid.UUID,
    budget_id: uuid.UUID,
    allocations: list[dict],
) -> list[TransactionAllocation] | None:
    """
    Allocate a transaction to one or more amount patterns or occurrences.

    This replaces all existing allocations for the transaction.

    Args:
        db: Database session
        transaction_id: Transaction ID to allocate
        budget_id: Budget ID (for authorization check)
        allocations: List of allocation dicts with keys:
            - amount_pattern_id: UUID of amount pattern (for active period)
            - amount_occurrence_id: UUID of amount occurrence (for archived period)
            - amount: int amount in øre (can be None if is_remainder)
            - is_remainder: bool whether this is the remainder allocation

    Returns:
        List of created TransactionAllocation instances, or None if validation fails

    Raises:
        ValueError: If validation fails (with descriptive message)
    """
    # Get and verify transaction
    transaction = get_transaction_by_id(db, transaction_id, budget_id)
    if not transaction:
        raise ValueError("Transaction not found")

    # If no allocations, clear existing and set status to uncategorized
    if not allocations:
        # Delete existing allocations
        db.query(TransactionAllocation).filter(
            TransactionAllocation.transaction_id == transaction_id
        ).delete()

        # Update transaction status
        transaction.status = TransactionStatus.UNCATEGORIZED
        db.commit()

        return []

    # Validate: only one allocation can be remainder
    remainder_count = sum(1 for alloc in allocations if alloc.get("is_remainder", False))
    if remainder_count > 1:
        raise ValueError("Only one allocation can be marked as remainder")

    # Validate and collect pattern/occurrence IDs
    pattern_ids = []
    occurrence_ids = []

    for alloc in allocations:
        pattern_id = alloc.get("amount_pattern_id")
        occurrence_id = alloc.get("amount_occurrence_id")

        # Exactly one must be set
        if not pattern_id and not occurrence_id:
            raise ValueError("Either amount_pattern_id or amount_occurrence_id must be set")
        if pattern_id and occurrence_id:
            raise ValueError("Cannot set both amount_pattern_id and amount_occurrence_id")

        if pattern_id:
            pattern_ids.append(uuid.UUID(pattern_id))
        if occurrence_id:
            occurrence_ids.append(uuid.UUID(occurrence_id))

    # Verify all amount patterns exist and belong to budget posts in same budget
    if pattern_ids:
        patterns = db.query(AmountPattern).join(
            AmountPattern.budget_post
        ).filter(
            AmountPattern.id.in_(pattern_ids),
            AmountPattern.budget_post.has(budget_id=budget_id, deleted_at=None),
        ).all()

        if len(patterns) != len(pattern_ids):
            raise ValueError("One or more amount patterns not found or don't belong to this budget")

    # Verify all amount occurrences exist and belong to archived budget posts in same budget
    if occurrence_ids:
        occurrences = db.query(AmountOccurrence).join(
            AmountOccurrence.archived_budget_post
        ).filter(
            AmountOccurrence.id.in_(occurrence_ids),
            AmountOccurrence.archived_budget_post.has(budget_id=budget_id),
        ).all()

        if len(occurrences) != len(occurrence_ids):
            raise ValueError("One or more amount occurrences not found or don't belong to this budget")

    # Build allocation amounts
    allocation_amounts = {}
    remainder_target_id = None

    for alloc in allocations:
        pattern_id = alloc.get("amount_pattern_id")
        occurrence_id = alloc.get("amount_occurrence_id")
        target_id = uuid.UUID(pattern_id) if pattern_id else uuid.UUID(occurrence_id)
        is_remainder = alloc.get("is_remainder", False)

        if is_remainder:
            remainder_target_id = target_id
        else:
            if alloc.get("amount") is None:
                raise ValueError("Amount is required for non-remainder allocations")
            allocation_amounts[target_id] = alloc["amount"]

    # Calculate remainder if present
    if remainder_target_id:
        sum_allocated = sum(allocation_amounts.values())
        remainder_amount = abs(transaction.amount) - sum_allocated

        if remainder_amount < 0:
            raise ValueError("Sum of allocations exceeds transaction amount")

        allocation_amounts[remainder_target_id] = remainder_amount
    else:
        # No remainder: sum must equal transaction amount
        sum_allocated = sum(allocation_amounts.values())
        if sum_allocated != abs(transaction.amount):
            raise ValueError(
                f"Sum of allocations ({sum_allocated}) must equal transaction amount ({abs(transaction.amount)})"
            )

    # Delete existing allocations
    db.query(TransactionAllocation).filter(
        TransactionAllocation.transaction_id == transaction_id
    ).delete()

    # Create new allocations
    new_allocations = []
    for alloc in allocations:
        pattern_id = alloc.get("amount_pattern_id")
        occurrence_id = alloc.get("amount_occurrence_id")
        target_id = uuid.UUID(pattern_id) if pattern_id else uuid.UUID(occurrence_id)
        is_remainder = alloc.get("is_remainder", False)

        allocation = TransactionAllocation(
            transaction_id=transaction_id,
            amount_pattern_id=uuid.UUID(pattern_id) if pattern_id else None,
            amount_occurrence_id=uuid.UUID(occurrence_id) if occurrence_id else None,
            amount=allocation_amounts[target_id],
            is_remainder=is_remainder,
        )
        db.add(allocation)
        new_allocations.append(allocation)

    # Update transaction status to categorized
    transaction.status = TransactionStatus.CATEGORIZED

    db.commit()

    # Refresh all allocations to get timestamps
    for allocation in new_allocations:
        db.refresh(allocation)

    return new_allocations
