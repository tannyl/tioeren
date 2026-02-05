"""Forecast routes for balance projections."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.forecast import ForecastResponse, MonthProjectionResponse, LowestPointResponse, LargeExpenseResponse
from api.services.forecast_service import calculate_forecast
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets", tags=["forecast"])


@router.get(
    "/{budget_id}/forecast",
    response_model=ForecastResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        422: {"description": "Invalid parameters"},
    },
)
def get_budget_forecast(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    months: int = Query(default=12, ge=1, le=24, description="Number of months to project forward"),
) -> ForecastResponse:
    """
    Get forecast projection for a budget.

    Returns projected balance for N months forward based on:
    - Current account balances
    - Expected budget post occurrences
    - Recurrence patterns

    Includes insights:
    - Lowest balance point in the forecast period
    - Next large expense (within next 3 months)

    Only the budget owner can access the forecast.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Verify budget exists and user has access
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Calculate forecast
    forecast_result = calculate_forecast(db, budget_uuid, months)

    # Convert dataclass projections to response models
    projection_responses = [
        MonthProjectionResponse(
            month=proj.month,
            start_balance=proj.start_balance,
            expected_income=proj.expected_income,
            expected_expenses=proj.expected_expenses,
            end_balance=proj.end_balance,
        )
        for proj in forecast_result.projections
    ]

    # Convert lowest point dict to response model
    lowest_point_response = LowestPointResponse(
        month=forecast_result.lowest_point["month"],
        balance=forecast_result.lowest_point["balance"],
    )

    # Convert next large expense if present
    next_large_expense_response = None
    if forecast_result.next_large_expense:
        next_large_expense_response = LargeExpenseResponse(
            name=forecast_result.next_large_expense["name"],
            amount=forecast_result.next_large_expense["amount"],
            date=forecast_result.next_large_expense["date"],
        )

    return ForecastResponse(
        projections=projection_responses,
        lowest_point=lowest_point_response,
        next_large_expense=next_large_expense_response,
    )
