"""Transaction service layer for business logic."""

import base64
import json
import uuid
from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.models.transaction import Transaction, TransactionStatus
from api.models.account import Account


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
) -> tuple[list[Transaction], str | None]:
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
        Tuple of (list of transactions, next cursor or None)
    """
    # Start with base query - join with accounts to filter by budget
    query = db.query(Transaction).join(Account).filter(
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
    transactions = query.limit(limit + 1).all()

    # Determine next cursor
    next_cursor = None
    if len(transactions) > limit:
        last_transaction = transactions[limit - 1]
        next_cursor = encode_cursor(last_transaction.date, last_transaction.id)
        transactions = transactions[:limit]

    return transactions, next_cursor


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
