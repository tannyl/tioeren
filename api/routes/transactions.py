"""Transaction routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.models.transaction import TransactionStatus
from api.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
)
from api.services.transaction_service import (
    get_budget_transactions,
    create_transaction,
    get_transaction_by_id,
    update_transaction,
    delete_transaction,
)
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets/{budget_id}/transactions", tags=["transactions"])


def verify_budget_access(budget_id: str, current_user: CurrentUser, db: Session) -> uuid.UUID:
    """
    Verify user has access to budget and return UUID.

    Args:
        budget_id: Budget ID string
        current_user: Current authenticated user
        db: Database session

    Returns:
        Budget UUID

    Raises:
        HTTPException: If budget not found or not accessible
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    return budget_uuid


@router.get(
    "",
    response_model=TransactionListResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_transactions(
    budget_id: str,
    current_user: CurrentUser,
    account_id: str | None = Query(None, description="Filter by account UUID"),
    status_filter: TransactionStatus | None = Query(None, alias="status", description="Filter by status"),
    date_from: date | None = Query(None, description="Filter by start date"),
    date_to: date | None = Query(None, description="Filter by end date"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    """
    List transactions for a budget with filtering and pagination.

    Supports filtering by:
    - account_id: Filter transactions for specific account
    - status: Filter by transaction status
    - date_from/date_to: Filter by date range

    Returns paginated list sorted by date DESC, then id DESC.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    # Parse account_id if provided
    account_uuid = None
    if account_id:
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid account_id format",
            )

    transactions, next_cursor = get_budget_transactions(
        db=db,
        budget_id=budget_uuid,
        account_id=account_uuid,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor=cursor,
    )

    return TransactionListResponse(
        data=[
            TransactionResponse(
                id=str(transaction.id),
                account_id=str(transaction.account_id),
                date=transaction.date,
                amount=transaction.amount,
                description=transaction.description,
                status=transaction.status,
                is_internal_transfer=transaction.is_internal_transfer,
                counterpart_transaction_id=str(transaction.counterpart_transaction_id)
                if transaction.counterpart_transaction_id
                else None,
                external_id=transaction.external_id,
                import_hash=transaction.import_hash,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
            for transaction in transactions
        ],
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or account not found"},
        422: {"description": "Validation error"},
    },
)
def create_transaction_endpoint(
    budget_id: str,
    transaction_data: TransactionCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Create a new transaction.

    If is_internal_transfer is true and counterpart_account_id is provided,
    creates two linked transactions (one negative, one positive).

    Internal transfers are automatically marked as categorized.
    Regular transactions start as uncategorized.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    # Parse account_id
    try:
        account_uuid = uuid.UUID(transaction_data.account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account_id format",
        )

    # Parse counterpart_account_id if provided
    counterpart_uuid = None
    if transaction_data.counterpart_account_id:
        try:
            counterpart_uuid = uuid.UUID(transaction_data.counterpart_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid counterpart_account_id format",
            )

    transaction = create_transaction(
        db=db,
        account_id=account_uuid,
        budget_id=budget_uuid,
        user_id=current_user.id,
        transaction_date=transaction_data.date,
        amount=transaction_data.amount,
        description=transaction_data.description,
        is_internal_transfer=transaction_data.is_internal_transfer,
        counterpart_account_id=counterpart_uuid,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or does not belong to this budget",
        )

    return TransactionResponse(
        id=str(transaction.id),
        account_id=str(transaction.account_id),
        date=transaction.date,
        amount=transaction.amount,
        description=transaction.description,
        status=transaction.status,
        is_internal_transfer=transaction.is_internal_transfer,
        counterpart_transaction_id=str(transaction.counterpart_transaction_id)
        if transaction.counterpart_transaction_id
        else None,
        external_id=transaction.external_id,
        import_hash=transaction.import_hash,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or transaction not found"},
    },
)
def get_transaction(
    budget_id: str,
    transaction_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Get a single transaction by ID.

    Returns 404 if transaction not found or doesn't belong to the budget.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        transaction_uuid = uuid.UUID(transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    transaction = get_transaction_by_id(db, transaction_uuid, budget_uuid)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransactionResponse(
        id=str(transaction.id),
        account_id=str(transaction.account_id),
        date=transaction.date,
        amount=transaction.amount,
        description=transaction.description,
        status=transaction.status,
        is_internal_transfer=transaction.is_internal_transfer,
        counterpart_transaction_id=str(transaction.counterpart_transaction_id)
        if transaction.counterpart_transaction_id
        else None,
        external_id=transaction.external_id,
        import_hash=transaction.import_hash,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or transaction not found"},
        422: {"description": "Validation error"},
    },
)
def update_transaction_endpoint(
    budget_id: str,
    transaction_id: str,
    transaction_data: TransactionUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Update a transaction.

    Cannot change account_id (would break internal transfers).
    Updates updated_at and updated_by automatically.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        transaction_uuid = uuid.UUID(transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    transaction = update_transaction(
        db=db,
        transaction_id=transaction_uuid,
        budget_id=budget_uuid,
        user_id=current_user.id,
        transaction_date=transaction_data.date,
        amount=transaction_data.amount,
        description=transaction_data.description,
        status=transaction_data.status,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransactionResponse(
        id=str(transaction.id),
        account_id=str(transaction.account_id),
        date=transaction.date,
        amount=transaction.amount,
        description=transaction.description,
        status=transaction.status,
        is_internal_transfer=transaction.is_internal_transfer,
        counterpart_transaction_id=str(transaction.counterpart_transaction_id)
        if transaction.counterpart_transaction_id
        else None,
        external_id=transaction.external_id,
        import_hash=transaction.import_hash,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or transaction not found"},
    },
)
def delete_transaction_endpoint(
    budget_id: str,
    transaction_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a transaction (hard delete).

    If the transaction is an internal transfer, both linked transactions are deleted.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        transaction_uuid = uuid.UUID(transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    success = delete_transaction(db, transaction_uuid, budget_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
