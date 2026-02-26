"""Dashboard routes for aggregated budget data."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.dashboard import DashboardResponse
from api.services.dashboard_service import get_dashboard_data
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets", tags=["dashboard"])


@router.get(
    "/{budget_id}/dashboard",
    response_model=DashboardResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def get_budget_dashboard(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """
    Get dashboard data for a budget.

    Returns aggregated data:
    - Available balance (sum of cashbox containers)
    - All containers with current balances
    - Month summary (income/expenses)
    - Pending transactions count

    Only the budget owner can access the dashboard.
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

    # Get dashboard data
    dashboard_data = get_dashboard_data(db, budget_uuid)

    return DashboardResponse(**dashboard_data)
