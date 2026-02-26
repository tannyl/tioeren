"""Dashboard schemas for response validation."""

from pydantic import BaseModel, Field

from api.models.container import ContainerType


class ContainerBalance(BaseModel):
    """Container with current balance for dashboard."""

    id: str
    name: str
    type: ContainerType
    balance: int = Field(..., description="Current balance in øre (starting_balance + sum of transactions)")


class MonthSummary(BaseModel):
    """Summary of income and expenses for current month."""

    income: int = Field(..., description="Total income in øre (positive amounts)")
    expenses: int = Field(..., description="Total expenses in øre (negative amounts)")
    net: int = Field(..., description="Net amount (income + expenses) in øre")


class DashboardResponse(BaseModel):
    """Dashboard data for a budget."""

    available_balance: int = Field(
        ...,
        description="Sum of current balance for all containers with type='cashbox' (in øre)"
    )
    containers: list[ContainerBalance] = Field(..., description="All containers with current balances")
    month_summary: MonthSummary = Field(..., description="Income/expenses summary for current month")
    pending_count: int = Field(..., description="Count of uncategorized transactions")
