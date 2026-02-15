"""Budget post routes."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.budget_post import (
    BudgetPostCreate,
    BudgetPostUpdate,
    BudgetPostResponse,
    BudgetPostListResponse,
    OccurrenceResponse,
    BudgetPostOccurrencesResponse,
    BulkOccurrencesResponse,
    AmountPatternResponse,
    PreviewOccurrencesRequest,
    PreviewOccurrencesResponse,
    PreviewOccurrenceResponse,
)
from api.services.budget_post_service import (
    create_budget_post,
    get_budget_posts,
    get_budget_post_by_id,
    update_budget_post,
    soft_delete_budget_post,
    expand_amount_patterns_to_occurrences,
    expand_patterns_from_data,
    BudgetPostValidationError,
    BudgetPostConflictError,
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


def _build_budget_post_response(post) -> BudgetPostResponse:
    """
    Build BudgetPostResponse from a BudgetPost model instance.

    Args:
        post: BudgetPost model instance

    Returns:
        BudgetPostResponse schema instance
    """
    return BudgetPostResponse(
        id=str(post.id),
        budget_id=str(post.budget_id),
        direction=post.direction,
        category_id=str(post.category_id) if post.category_id else None,
        category_name=post.category.name if post.category else None,
        type=post.type,
        accumulate=post.accumulate,
        counterparty_type=post.counterparty_type,
        counterparty_account_id=str(post.counterparty_account_id) if post.counterparty_account_id else None,
        transfer_from_account_id=str(post.transfer_from_account_id) if post.transfer_from_account_id else None,
        transfer_to_account_id=str(post.transfer_to_account_id) if post.transfer_to_account_id else None,
        amount_patterns=[
            AmountPatternResponse(
                id=str(pattern.id),
                budget_post_id=str(pattern.budget_post_id),
                amount=pattern.amount,
                start_date=pattern.start_date.isoformat(),
                end_date=pattern.end_date.isoformat() if pattern.end_date else None,
                recurrence_pattern=pattern.recurrence_pattern,
                account_ids=pattern.account_ids,
                created_at=pattern.created_at,
                updated_at=pattern.updated_at,
            )
            for pattern in post.amount_patterns
        ],
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


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
        data=[_build_budget_post_response(post) for post in posts],
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

    # Parse category_id if provided
    category_uuid = None
    if post_data.category_id:
        try:
            category_uuid = uuid.UUID(post_data.category_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id format",
            )

    # Parse account IDs if provided
    counterparty_account_uuid = None
    if post_data.counterparty_account_id:
        try:
            counterparty_account_uuid = uuid.UUID(post_data.counterparty_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid counterparty_account_id format",
            )

    transfer_from_account_uuid = None
    if post_data.transfer_from_account_id:
        try:
            transfer_from_account_uuid = uuid.UUID(post_data.transfer_from_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transfer_from_account_id format",
            )

    transfer_to_account_uuid = None
    if post_data.transfer_to_account_id:
        try:
            transfer_to_account_uuid = uuid.UUID(post_data.transfer_to_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transfer_to_account_id format",
            )

    # Convert amount_patterns to dicts (required)
    amount_patterns_dicts = []
    if post_data.amount_patterns:
        amount_patterns_dicts = []
        for pattern in post_data.amount_patterns:
            pattern_dict = {
                "amount": pattern.amount,
                "start_date": pattern.start_date,
                "end_date": pattern.end_date,
                "account_ids": pattern.account_ids,
            }
            if pattern.recurrence_pattern:
                pattern_dict["recurrence_pattern"] = pattern.recurrence_pattern.model_dump(exclude_none=True)
            amount_patterns_dicts.append(pattern_dict)

    try:
        budget_post = create_budget_post(
            db=db,
            budget_id=budget_uuid,
            user_id=current_user.id,
            direction=post_data.direction,
            post_type=post_data.type,
            category_id=category_uuid,
            accumulate=post_data.accumulate,
            counterparty_type=post_data.counterparty_type,
            counterparty_account_id=counterparty_account_uuid,
            transfer_from_account_id=transfer_from_account_uuid,
            transfer_to_account_id=transfer_to_account_uuid,
            amount_patterns=amount_patterns_dicts,
        )
    except BudgetPostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except BudgetPostConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    if not budget_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category or account not found or does not belong to this budget",
        )

    return _build_budget_post_response(budget_post)


@router.get(
    "/occurrences",
    response_model=BulkOccurrencesResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        422: {"description": "Invalid date format"},
    },
)
def get_bulk_budget_post_occurrences(
    budget_id: str,
    current_user: CurrentUser,
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD), defaults to first day of current month"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD), defaults to last day of current month"),
    db: Session = Depends(get_db),
) -> BulkOccurrencesResponse:
    """
    Get occurrences for all budget posts in a budget.

    Useful for generating monthly forecast views showing all expected transactions.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    # Parse dates or default to current month
    try:
        if from_date:
            start_date = date.fromisoformat(from_date)
        else:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if to_date:
            end_date = date.fromisoformat(to_date)
        else:
            today = date.today()
            # Get last day of current month
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                end_date = next_month - timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Get all budget posts for this budget
    posts, _ = get_budget_posts(db, budget_uuid, limit=1000)  # Get all posts

    result = []
    for post in posts:
        # Use new expand_amount_patterns_to_occurrences which returns (date, amount) tuples
        occurrence_tuples = expand_amount_patterns_to_occurrences(post, start_date, end_date)

        occurrences = [
            OccurrenceResponse(
                date=d.isoformat(),
                amount=amount,
            )
            for d, amount in occurrence_tuples
        ]

        result.append(
            BudgetPostOccurrencesResponse(
                budget_post_id=str(post.id),
                occurrences=occurrences,
            )
        )

    return BulkOccurrencesResponse(data=result)


@router.post(
    "/preview-occurrences",
    response_model=PreviewOccurrencesResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        422: {"description": "Invalid date format or pattern data"},
    },
)
def preview_budget_post_occurrences(
    budget_id: str,
    request: PreviewOccurrencesRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> PreviewOccurrencesResponse:
    """
    Preview occurrences from pattern data without creating a budget post.

    Useful for visualizing patterns in the UI before saving.
    """
    # Verify user has access to the budget
    verify_budget_access(budget_id, current_user, db)

    # Parse date range
    try:
        start_date = date.fromisoformat(request.from_date)
        end_date = date.fromisoformat(request.to_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Convert AmountPatternCreate objects to dicts for the service function
    pattern_dicts = []
    for pattern in request.amount_patterns:
        pattern_dict = {
            "amount": pattern.amount,
            "start_date": pattern.start_date,
            "end_date": pattern.end_date,
            "recurrence_pattern": pattern.recurrence_pattern.model_dump(exclude_none=True) if pattern.recurrence_pattern else None,
        }
        pattern_dicts.append(pattern_dict)

    # Expand patterns to occurrences
    occurrence_tuples = expand_patterns_from_data(pattern_dicts, start_date, end_date)

    # Convert to response format
    occurrences = [
        PreviewOccurrenceResponse(
            date=d.isoformat(),
            amount=amount,
            pattern_index=pattern_index,
        )
        for d, amount, pattern_index in occurrence_tuples
    ]

    return PreviewOccurrencesResponse(occurrences=occurrences)


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

    return _build_budget_post_response(budget_post)


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

    # Parse account IDs if provided
    counterparty_account_uuid = None
    if post_data.counterparty_account_id is not None:
        try:
            counterparty_account_uuid = uuid.UUID(post_data.counterparty_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid counterparty_account_id format",
            )

    transfer_from_account_uuid = None
    if post_data.transfer_from_account_id is not None:
        try:
            transfer_from_account_uuid = uuid.UUID(post_data.transfer_from_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transfer_from_account_id format",
            )

    transfer_to_account_uuid = None
    if post_data.transfer_to_account_id is not None:
        try:
            transfer_to_account_uuid = uuid.UUID(post_data.transfer_to_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transfer_to_account_id format",
            )

    # Convert amount_patterns to dicts if provided
    amount_patterns_dicts = None
    if post_data.amount_patterns is not None:
        amount_patterns_dicts = []
        for pattern in post_data.amount_patterns:
            pattern_dict = {
                "amount": pattern.amount,
                "start_date": pattern.start_date,
                "end_date": pattern.end_date,
                "account_ids": pattern.account_ids,
            }
            if pattern.recurrence_pattern:
                pattern_dict["recurrence_pattern"] = pattern.recurrence_pattern.model_dump(exclude_none=True)
            amount_patterns_dicts.append(pattern_dict)

    try:
        budget_post = update_budget_post(
            db=db,
            post_id=post_uuid,
            budget_id=budget_uuid,
            user_id=current_user.id,
            post_type=post_data.type,
            accumulate=post_data.accumulate,
            counterparty_type=post_data.counterparty_type,
            counterparty_account_id=counterparty_account_uuid,
            transfer_from_account_id=transfer_from_account_uuid,
            transfer_to_account_id=transfer_to_account_uuid,
            amount_patterns=amount_patterns_dicts,
        )
    except BudgetPostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except BudgetPostConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    if not budget_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget post not found or category/account does not belong to this budget",
        )

    return _build_budget_post_response(budget_post)


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


@router.get(
    "/{post_id}/occurrences",
    response_model=BudgetPostOccurrencesResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or budget post not found"},
        422: {"description": "Invalid date format"},
    },
)
def get_budget_post_occurrences(
    budget_id: str,
    post_id: str,
    current_user: CurrentUser,
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD), defaults to first day of current month"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD), defaults to last day of current month"),
    db: Session = Depends(get_db),
) -> BudgetPostOccurrencesResponse:
    """
    Get concrete occurrence dates for a budget post.

    Expands recurrence pattern into specific dates within the date range.
    Returns amount_min or amount_max for each occurrence.
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

    # Parse dates or default to current month
    try:
        if from_date:
            start_date = date.fromisoformat(from_date)
        else:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if to_date:
            end_date = date.fromisoformat(to_date)
        else:
            today = date.today()
            # Get last day of current month
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                end_date = next_month - timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Expand occurrences using new expand_amount_patterns_to_occurrences
    occurrence_tuples = expand_amount_patterns_to_occurrences(budget_post, start_date, end_date)

    occurrences = [
        OccurrenceResponse(
            date=d.isoformat(),
            amount=amount,
        )
        for d, amount in occurrence_tuples
    ]

    return BudgetPostOccurrencesResponse(
        budget_post_id=str(budget_post.id),
        occurrences=occurrences,
    )
