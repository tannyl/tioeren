"""Budget routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetListResponse,
)
from api.services.budget_service import (
    create_budget,
    get_user_budgets,
    get_budget_by_id,
    update_budget,
    soft_delete_budget,
)


router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get(
    "",
    response_model=BudgetListResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
def list_budgets(
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    db: Session = Depends(get_db),
) -> BudgetListResponse:
    """
    List all budgets for the authenticated user.

    Returns paginated list with cursor for next page.
    """
    budgets, next_cursor = get_user_budgets(db, current_user.id, limit, cursor)

    return BudgetListResponse(
        data=[
            BudgetResponse(
                id=str(budget.id),
                name=budget.name,
                owner_id=str(budget.owner_id),
                warning_threshold=budget.warning_threshold,
                created_at=budget.created_at,
                updated_at=budget.updated_at,
            )
            for budget in budgets
        ],
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
def create_budget_endpoint(
    budget_data: BudgetCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetResponse:
    """
    Create a new budget.

    New budgets start empty - no default categories or posts.
    Users add their own budget posts with category paths as needed.
    """
    budget = create_budget(
        db=db,
        name=budget_data.name,
        owner_id=current_user.id,
        warning_threshold=budget_data.warning_threshold,
    )

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        owner_id=str(budget.owner_id),
        warning_threshold=budget.warning_threshold,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def get_budget(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetResponse:
    """
    Get a single budget by ID.

    Returns 403 if user is not the owner.
    Returns 404 if budget not found or soft-deleted.
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

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        owner_id=str(budget.owner_id),
        warning_threshold=budget.warning_threshold,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to modify this budget"},
        404: {"description": "Budget not found"},
        422: {"description": "Validation error"},
    },
)
def update_budget_endpoint(
    budget_id: str,
    budget_data: BudgetUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetResponse:
    """
    Update a budget.

    Only the owner can update the budget.
    Returns 404 if budget not found or soft-deleted.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    budget = update_budget(
        db=db,
        budget_id=budget_uuid,
        user_id=current_user.id,
        name=budget_data.name,
        warning_threshold=budget_data.warning_threshold,
    )

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        owner_id=str(budget.owner_id),
        warning_threshold=budget.warning_threshold,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this budget"},
        404: {"description": "Budget not found"},
    },
)
def delete_budget(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete a budget.

    Only the owner can delete the budget.
    Returns 404 if budget not found or already deleted.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    success = soft_delete_budget(db, budget_uuid, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
