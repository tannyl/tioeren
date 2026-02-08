"""Budget post routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.budget_post import (
    BudgetPostCreate,
    BudgetPostUpdate,
    BudgetPostResponse,
    BudgetPostListResponse,
)
from api.services.budget_post_service import (
    create_budget_post,
    get_budget_posts,
    get_budget_post_by_id,
    update_budget_post,
    soft_delete_budget_post,
)
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets/{budget_id}/budget-posts", tags=["budget-posts"])


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
    response_model=BudgetPostListResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_budget_posts(
    budget_id: str,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    db: Session = Depends(get_db),
) -> BudgetPostListResponse:
    """
    List budget posts for a budget with pagination.

    Returns paginated list sorted by created_at DESC, then id DESC.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    posts, next_cursor = get_budget_posts(
        db=db,
        budget_id=budget_uuid,
        limit=limit,
        cursor=cursor,
    )

    return BudgetPostListResponse(
        data=[
            BudgetPostResponse(
                id=str(post.id),
                budget_id=str(post.budget_id),
                category_id=str(post.category_id),
                name=post.name,
                type=post.type,
                amount_min=post.amount_min,
                amount_max=post.amount_max,
                from_account_ids=post.from_account_ids,
                to_account_ids=post.to_account_ids,
                recurrence_pattern=post.recurrence_pattern,
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
            for post in posts
        ],
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=BudgetPostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or category not found"},
        422: {"description": "Validation error"},
    },
)
def create_budget_post_endpoint(
    budget_id: str,
    post_data: BudgetPostCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetPostResponse:
    """
    Create a new budget post.

    Validates that:
    - Category belongs to the same budget
    - All account IDs (if provided) belong to the same budget
    - Amount constraints are satisfied
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    # Parse category_id
    try:
        category_uuid = uuid.UUID(post_data.category_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category_id format",
        )

    # Parse from_account_ids if provided
    from_account_uuids = None
    if post_data.from_account_ids:
        try:
            from_account_uuids = [uuid.UUID(aid) for aid in post_data.from_account_ids]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid from_account_ids format",
            )

    # Parse to_account_ids if provided
    to_account_uuids = None
    if post_data.to_account_ids:
        try:
            to_account_uuids = [uuid.UUID(aid) for aid in post_data.to_account_ids]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid to_account_ids format",
            )

    # Convert recurrence_pattern to dict if provided
    recurrence_dict = None
    if post_data.recurrence_pattern:
        recurrence_dict = post_data.recurrence_pattern.model_dump(exclude_none=True)

    budget_post = create_budget_post(
        db=db,
        budget_id=budget_uuid,
        user_id=current_user.id,
        category_id=category_uuid,
        name=post_data.name,
        post_type=post_data.type,
        amount_min=post_data.amount_min,
        amount_max=post_data.amount_max,
        from_account_ids=from_account_uuids,
        to_account_ids=to_account_uuids,
        recurrence_pattern=recurrence_dict,
    )

    if not budget_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category or account not found or does not belong to this budget",
        )

    return BudgetPostResponse(
        id=str(budget_post.id),
        budget_id=str(budget_post.budget_id),
        category_id=str(budget_post.category_id),
        name=budget_post.name,
        type=budget_post.type,
        amount_min=budget_post.amount_min,
        amount_max=budget_post.amount_max,
        from_account_ids=budget_post.from_account_ids,
        to_account_ids=budget_post.to_account_ids,
        recurrence_pattern=budget_post.recurrence_pattern,
        created_at=budget_post.created_at,
        updated_at=budget_post.updated_at,
    )


@router.get(
    "/{post_id}",
    response_model=BudgetPostResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or budget post not found"},
    },
)
def get_budget_post(
    budget_id: str,
    post_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetPostResponse:
    """
    Get a single budget post by ID.

    Returns 404 if budget post not found or doesn't belong to the budget.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )

    budget_post = get_budget_post_by_id(db, post_uuid, budget_uuid)

    if not budget_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )

    return BudgetPostResponse(
        id=str(budget_post.id),
        budget_id=str(budget_post.budget_id),
        category_id=str(budget_post.category_id),
        name=budget_post.name,
        type=budget_post.type,
        amount_min=budget_post.amount_min,
        amount_max=budget_post.amount_max,
        from_account_ids=budget_post.from_account_ids,
        to_account_ids=budget_post.to_account_ids,
        recurrence_pattern=budget_post.recurrence_pattern,
        created_at=budget_post.created_at,
        updated_at=budget_post.updated_at,
    )


@router.put(
    "/{post_id}",
    response_model=BudgetPostResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or budget post not found"},
        422: {"description": "Validation error"},
    },
)
def update_budget_post_endpoint(
    budget_id: str,
    post_id: str,
    post_data: BudgetPostUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BudgetPostResponse:
    """
    Update a budget post.

    All fields are optional. Only provided fields will be updated.
    Updates updated_at and updated_by automatically.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )

    # Parse category_id if provided
    category_uuid = None
    if post_data.category_id is not None:
        try:
            category_uuid = uuid.UUID(post_data.category_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id format",
            )

    # Parse from_account_ids if provided
    from_account_uuids = None
    if post_data.from_account_ids is not None:
        if post_data.from_account_ids:  # Non-empty list
            try:
                from_account_uuids = [uuid.UUID(aid) for aid in post_data.from_account_ids]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid from_account_ids format",
                )
        else:  # Empty list - clear the field
            from_account_uuids = []

    # Parse to_account_ids if provided
    to_account_uuids = None
    if post_data.to_account_ids is not None:
        if post_data.to_account_ids:  # Non-empty list
            try:
                to_account_uuids = [uuid.UUID(aid) for aid in post_data.to_account_ids]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid to_account_ids format",
                )
        else:  # Empty list - clear the field
            to_account_uuids = []

    # Convert recurrence_pattern to dict if provided
    recurrence_dict = None
    if post_data.recurrence_pattern is not None:
        recurrence_dict = post_data.recurrence_pattern.model_dump(exclude_none=True)

    # Validate amount_min <= amount_max for update
    # We need to check the current values and the updated values
    current_post = get_budget_post_by_id(db, post_uuid, budget_uuid)
    if not current_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )

    # Determine final amount_min and amount_max after update
    final_amount_min = post_data.amount_min if post_data.amount_min is not None else current_post.amount_min
    final_amount_max = post_data.amount_max if post_data.amount_max is not None else current_post.amount_max

    # Validate min <= max if both are set
    if final_amount_max is not None and final_amount_min > final_amount_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount_max must be greater than or equal to amount_min",
        )

    budget_post = update_budget_post(
        db=db,
        post_id=post_uuid,
        budget_id=budget_uuid,
        user_id=current_user.id,
        category_id=category_uuid,
        name=post_data.name,
        post_type=post_data.type,
        amount_min=post_data.amount_min,
        amount_max=post_data.amount_max,
        from_account_ids=from_account_uuids,
        to_account_ids=to_account_uuids,
        recurrence_pattern=recurrence_dict,
    )

    if not budget_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found or category/account does not belong to this budget",
        )

    return BudgetPostResponse(
        id=str(budget_post.id),
        budget_id=str(budget_post.budget_id),
        category_id=str(budget_post.category_id),
        name=budget_post.name,
        type=budget_post.type,
        amount_min=budget_post.amount_min,
        amount_max=budget_post.amount_max,
        from_account_ids=budget_post.from_account_ids,
        to_account_ids=budget_post.to_account_ids,
        recurrence_pattern=budget_post.recurrence_pattern,
        created_at=budget_post.created_at,
        updated_at=budget_post.updated_at,
    )


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or budget post not found"},
    },
)
def delete_budget_post(
    budget_id: str,
    post_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete a budget post.

    Sets deleted_at timestamp. Does not actually remove from database.
    Returns 404 if budget post not found or already deleted.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )

    success = soft_delete_budget_post(db, post_uuid, budget_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found",
        )
