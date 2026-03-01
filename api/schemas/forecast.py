"""Forecast schemas for response validation."""

from pydantic import BaseModel, Field


class MonthProjectionResponse(BaseModel):
    """Projection data for a single month."""

    month: str = Field(..., description="Month in YYYY-MM format")
    start_balance: int = Field(..., description="Starting balance for the month in øre")
    expected_income: int = Field(..., description="Expected income for the month in øre")
    expected_expenses: int = Field(..., description="Expected expenses for the month in øre (negative)")
    end_balance: int = Field(..., description="Ending balance for the month in øre")


class LowestPointResponse(BaseModel):
    """Information about the lowest balance point in the forecast period."""

    month: str = Field(..., description="Month with lowest balance (YYYY-MM format)")
    balance: int = Field(..., description="Lowest balance in øre")


class LargeExpenseResponse(BaseModel):
    """Information about the next large expense."""

    name: str = Field(..., description="Name of the budget post")
    amount: int = Field(..., description="Expected amount in øre (negative)")
    date: str = Field(..., description="Expected date (ISO format YYYY-MM-DD)")


class ContainerMonthProjectionResponse(BaseModel):
    """Per-container projection for a single month."""

    container_id: str = Field(..., description="Container UUID")
    container_name: str = Field(..., description="Container name")
    month: str = Field(..., description="Month in YYYY-MM format")
    start_balance: int = Field(..., description="Starting balance in øre")
    min_balance: int = Field(..., description="Minimum possible balance in øre (worst case)")
    estimate_balance: int = Field(..., description="Estimated balance in øre (point estimate)")
    max_balance: int = Field(..., description="Maximum possible balance in øre (best case)")


class ForecastResponse(BaseModel):
    """Forecast projection data for N months forward."""

    projections: list[MonthProjectionResponse] = Field(
        ..., description="Monthly projections for the forecast period"
    )
    container_projections: list[ContainerMonthProjectionResponse] = Field(
        ..., description="Per-container monthly projections with min/max intervals"
    )
    lowest_point: LowestPointResponse = Field(..., description="Information about the lowest balance point")
    next_large_expense: LargeExpenseResponse | None = Field(
        None, description="Information about the next large expense (within next 3 months)"
    )
