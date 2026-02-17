"""Bank days routes."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.deps.auth import CurrentUser
from api.utils.bank_days import is_bank_day


router = APIRouter(prefix="/bank-days", tags=["Bank Days"])


class NonBankDaysResponse(BaseModel):
    """Response schema for non-bank-days endpoint."""

    dates: list[str]


@router.get(
    "/non-bank-days",
    response_model=NonBankDaysResponse,
    responses={
        400: {"description": "Invalid date range or unsupported country code"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date format"},
    },
)
def get_non_bank_days(
    current_user: CurrentUser,
    from_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    country: str = Query("DK", description="ISO country code"),
) -> NonBankDaysResponse:
    """
    Get all non-bank-days (weekends + public holidays) within a date range.

    A non-bank-day is a day that is NOT a bank day (weekend or public holiday).
    Maximum range: 366 days.
    """
    # Parse dates
    try:
        start_date = date.fromisoformat(from_date)
        end_date = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Validate date range order
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be before or equal to to_date",
        )

    # Check max range (366 days)
    range_days = (end_date - start_date).days + 1  # +1 to include both endpoints
    if range_days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 366 days",
        )

    # Collect non-bank-days
    non_bank_days = []
    current_date = start_date

    try:
        while current_date <= end_date:
            if not is_bank_day(current_date, country):
                non_bank_days.append(current_date.isoformat())
            current_date += timedelta(days=1)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported country code: {country}",
        )

    return NonBankDaysResponse(dates=non_bank_days)
