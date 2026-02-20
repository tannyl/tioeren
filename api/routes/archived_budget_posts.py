"""Archived budget posts routes."""

import uuid
from datetime import date
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.budget_post import (
    ArchivedBudgetPostResponse,
    ArchivedBudgetPostListResponse,
    AmountOccurrenceResponse,
)
from api.services.budget_post_service import (
    get_budget_posts,
    create_archived_budget_post,
    get_archived_budget_posts,
    get_archived_budget_post_by_id,
)
from api.services.budget_service import get_budget_by_id
from api.models.archived_budget_post import ArchivedBudgetPost


# Helper function shared with budget_posts.py
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


# Router for archived budget posts GET endpoints
archived_router = APIRouter(
    prefix="/budgets/{budget_id}/archived-budget-posts",
    tags=["archived-budget-posts"]
)


@archived_router.get(
    "",
    response_model=ArchivedBudgetPostListResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_archived_budget_posts(
    budget_id: str,
    current_user: CurrentUser,
    year: int | None = Query(None, ge=2000, le=2100, description="Filter by year"),
    month: int | None = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    db: Session = Depends(get_db),
) -> ArchivedBudgetPostListResponse:
    """
    List archived budget posts for a budget, optionally filtered by period.

    Returns all archived budget posts, or only those for a specific year/month.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    archived_posts = get_archived_budget_posts(
        db=db,
        budget_id=budget_uuid,
        period_year=year,
        period_month=month,
    )

    return ArchivedBudgetPostListResponse(
        data=[
            ArchivedBudgetPostResponse(
                id=str(post.id),
                budget_id=str(post.budget_id),
                budget_post_id=str(post.budget_post_id) if post.budget_post_id else None,
                period_year=post.period_year,
                period_month=post.period_month,
                direction=post.direction,
                category_path=post.category_path,
                category_name=post.category_path[-1] if post.category_path else None,
                display_order=post.display_order,
                type=post.type,
                amount_occurrences=[
                    AmountOccurrenceResponse(
                        id=str(occ.id),
                        archived_budget_post_id=str(occ.archived_budget_post_id),
                        date=occ.date.isoformat() if occ.date else None,
                        amount=occ.amount,
                        created_at=occ.created_at,
                    )
                    for occ in post.amount_occurrences
                ],
                created_at=post.created_at,
            )
            for post in archived_posts
        ]
    )


@archived_router.get(
    "/{archived_post_id}",
    response_model=ArchivedBudgetPostResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or archived budget post not found"},
    },
)
def get_archived_budget_post(
    budget_id: str,
    archived_post_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ArchivedBudgetPostResponse:
    """
    Get a single archived budget post by ID.

    Returns 404 if archived budget post not found or doesn't belong to the budget.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    try:
        archived_uuid = uuid.UUID(archived_post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived budget post not found",
        )

    archived_post = get_archived_budget_post_by_id(db, archived_uuid, budget_uuid)

    if not archived_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived budget post not found",
        )

    return ArchivedBudgetPostResponse(
        id=str(archived_post.id),
        budget_id=str(archived_post.budget_id),
        budget_post_id=str(archived_post.budget_post_id) if archived_post.budget_post_id else None,
        period_year=archived_post.period_year,
        period_month=archived_post.period_month,
        direction=archived_post.direction,
        category_path=archived_post.category_path,
        category_name=archived_post.category_path[-1] if archived_post.category_path else None,
        display_order=archived_post.display_order,
        type=archived_post.type,
        amount_occurrences=[
            AmountOccurrenceResponse(
                id=str(occ.id),
                archived_budget_post_id=str(occ.archived_budget_post_id),
                date=occ.date.isoformat() if occ.date else None,
                amount=occ.amount,
                created_at=occ.created_at,
            )
            for occ in archived_post.amount_occurrences
        ],
        created_at=archived_post.created_at,
    )


# Router for archive action endpoint
archive_action_router = APIRouter(
    prefix="/budgets/{budget_id}",
    tags=["archived-budget-posts"]
)


class ArchivePeriodRequest(BaseModel):
    """Request schema for archiving a period."""
    year: int = Field(..., ge=2000, le=2100, description="Year to archive")
    month: int = Field(..., ge=1, le=12, description="Month to archive (1-12)")


@archive_action_router.post(
    "/archive-period",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        422: {"description": "Validation error"},
    },
)
def archive_period(
    budget_id: str,
    request_data: ArchivePeriodRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    """
    Manually archive all budget posts for a specific period.

    Creates archived snapshots of all active budget posts with their
    amount occurrences expanded for the specified period.

    In production, this would be handled by a scheduled job.
    """
    budget_uuid = verify_budget_access(budget_id, current_user, db)

    # Get all active budget posts for this budget
    posts, _ = get_budget_posts(db, budget_uuid, limit=1000)

    archived_count = 0
    skipped = 0

    for post in posts:
        # Check if already archived for this period
        existing = db.query(ArchivedBudgetPost).filter(
            ArchivedBudgetPost.budget_id == budget_uuid,
            ArchivedBudgetPost.budget_post_id == post.id,
            ArchivedBudgetPost.period_year == request_data.year,
            ArchivedBudgetPost.period_month == request_data.month,
        ).first()

        if existing:
            skipped += 1
            continue

        try:
            create_archived_budget_post(
                db=db,
                budget_id=budget_uuid,
                budget_post=post,
                period_year=request_data.year,
                period_month=request_data.month,
                user_id=current_user.id,
            )
            archived_count += 1
        except IntegrityError:
            # Race condition - another request archived it
            db.rollback()
            skipped += 1
            continue

    return {
        "message": f"Archived {archived_count} budget posts for {request_data.year}-{request_data.month:02d}",
        "archived_count": archived_count,
        "skipped_count": skipped,
    }
