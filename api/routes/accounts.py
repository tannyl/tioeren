"""Account routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
)
from api.services.account_service import (
    create_account,
    get_budget_accounts,
    get_account_by_id,
    update_account,
    soft_delete_account,
)
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets/{budget_id}/accounts", tags=["accounts"])


@router.get(
    "",
    response_model=AccountListResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_accounts(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> AccountListResponse:
    """
    List all accounts for a budget.

    Returns all non-deleted accounts. User must own the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    accounts = get_budget_accounts(db, budget_uuid)

    return AccountListResponse(
        data=[
            AccountResponse(
                id=str(account.id),
                budget_id=str(account.budget_id),
                name=account.name,
                purpose=account.purpose,
                datasource=account.datasource,
                currency=account.currency,
                starting_balance=account.starting_balance,
                credit_limit=account.credit_limit,
                locked=account.locked,
                current_balance=account.starting_balance,  # TODO: Calculate with transactions
                created_at=account.created_at,
                updated_at=account.updated_at,
            )
            for account in accounts
        ],
    )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        409: {"description": "Account with this name already exists in budget"},
        422: {"description": "Validation error"},
    },
)
def create_account_endpoint(
    budget_id: str,
    account_data: AccountCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    Create a new account in a budget.

    Validates purpose/datasource combinations and checks for duplicate names.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Create account
    try:
        account = create_account(
            db=db,
            budget_id=budget_uuid,
            user_id=current_user.id,
            name=account_data.name,
            purpose=account_data.purpose,
            datasource=account_data.datasource,
            starting_balance=account_data.starting_balance,
            currency=account_data.currency,
            credit_limit=account_data.credit_limit,
            locked=account_data.locked,
        )
    except ValueError as e:
        # Validation error (e.g., locked=True on non-savings account)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this name already exists in budget",
        )

    return AccountResponse(
        id=str(account.id),
        budget_id=str(account.budget_id),
        name=account.name,
        purpose=account.purpose,
        datasource=account.datasource,
        currency=account.currency,
        starting_balance=account.starting_balance,
        credit_limit=account.credit_limit,
        locked=account.locked,
        current_balance=account.starting_balance,  # TODO: Calculate with transactions
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or account not found"},
    },
)
def get_account(
    budget_id: str,
    account_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    Get a single account by ID.

    Returns 404 if account not found, soft-deleted, or doesn't belong to budget.
    Returns 403 if user doesn't own the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or account not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Get account
    account = get_account_by_id(db, account_uuid, budget_uuid)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return AccountResponse(
        id=str(account.id),
        budget_id=str(account.budget_id),
        name=account.name,
        purpose=account.purpose,
        datasource=account.datasource,
        currency=account.currency,
        starting_balance=account.starting_balance,
        credit_limit=account.credit_limit,
        locked=account.locked,
        current_balance=account.starting_balance,  # TODO: Calculate with transactions
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to modify this budget"},
        404: {"description": "Budget or account not found"},
        409: {"description": "Account with this name already exists in budget"},
        422: {"description": "Validation error"},
    },
)
def update_account_endpoint(
    budget_id: str,
    account_id: str,
    account_data: AccountUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    Update an account.

    Only the budget owner can update accounts.
    Returns 404 if account not found or soft-deleted.
    Returns 409 if name conflicts with another account in the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or account not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Build kwargs with only fields that were explicitly provided
    kwargs = {}
    if "name" in account_data.model_fields_set:
        kwargs["name"] = account_data.name
    if "purpose" in account_data.model_fields_set:
        kwargs["purpose"] = account_data.purpose
    if "datasource" in account_data.model_fields_set:
        kwargs["datasource"] = account_data.datasource
    if "currency" in account_data.model_fields_set:
        kwargs["currency"] = account_data.currency
    if "starting_balance" in account_data.model_fields_set:
        kwargs["starting_balance"] = account_data.starting_balance
    if "credit_limit" in account_data.model_fields_set:
        kwargs["credit_limit"] = account_data.credit_limit
    if "locked" in account_data.model_fields_set:
        kwargs["locked"] = account_data.locked

    # Update account
    try:
        account = update_account(
            db=db,
            account_id=account_uuid,
            budget_id=budget_uuid,
            user_id=current_user.id,
            **kwargs,
        )
    except ValueError as e:
        # Validation error (e.g., locked=True on non-savings account)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not account:
        # Check if it's a duplicate name issue by trying to get the original account
        original = get_account_by_id(db, account_uuid, budget_uuid)
        if original:
            # Account exists but update failed, likely due to duplicate name
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account with this name already exists in budget",
            )
        else:
            # Account doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

    return AccountResponse(
        id=str(account.id),
        budget_id=str(account.budget_id),
        name=account.name,
        purpose=account.purpose,
        datasource=account.datasource,
        currency=account.currency,
        starting_balance=account.starting_balance,
        credit_limit=account.credit_limit,
        locked=account.locked,
        current_balance=account.starting_balance,  # TODO: Calculate with transactions
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this account"},
        404: {"description": "Budget or account not found"},
    },
)
def delete_account(
    budget_id: str,
    account_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete an account.

    Only the budget owner can delete accounts.
    Returns 404 if account not found or already deleted.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or account not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Delete account
    success = soft_delete_account(db, account_uuid, budget_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
