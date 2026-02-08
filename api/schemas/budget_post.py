"""Budget post schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.models.budget_post import BudgetPostType


class RecurrencePattern(BaseModel):
    """Schema for recurrence pattern configuration."""

    type: str = Field(..., description="Recurrence type: monthly, quarterly, yearly, once")
    day: int | None = Field(None, ge=1, le=31, description="Day of month (1-31)")
    months: list[int] | None = Field(None, description="Months for quarterly/yearly (1-12)")
    date: str | None = Field(None, description="ISO date string for 'once' type")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate recurrence type."""
        valid_types = {"monthly", "quarterly", "yearly", "once"}
        if v not in valid_types:
            raise ValueError(f"type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("months")
    @classmethod
    def validate_months(cls, v: list[int] | None) -> list[int] | None:
        """Validate months are in range 1-12."""
        if v is not None:
            if not all(1 <= month <= 12 for month in v):
                raise ValueError("All months must be between 1 and 12")
        return v


class BudgetPostCreate(BaseModel):
    """Request schema for creating a budget post."""

    category_id: str = Field(..., description="Category UUID")
    name: str = Field(..., min_length=1, max_length=255)
    type: BudgetPostType = Field(..., description="Budget post type: fixed, ceiling, rolling")
    amount_min: int = Field(..., ge=0, description="Minimum amount in øre")
    amount_max: int | None = Field(None, ge=0, description="Maximum amount in øre (optional)")
    from_account_ids: list[str] | None = Field(None, description="List of account UUIDs (source)")
    to_account_ids: list[str] | None = Field(None, description="List of account UUIDs (destination)")
    recurrence_pattern: RecurrencePattern | None = Field(None, description="Recurrence configuration")

    @field_validator("amount_max")
    @classmethod
    def validate_amount_max(cls, v: int | None, info) -> int | None:
        """Validate amount_max >= amount_min when both provided."""
        if v is not None and "amount_min" in info.data:
            amount_min = info.data["amount_min"]
            if v < amount_min:
                raise ValueError("amount_max must be greater than or equal to amount_min")
        return v


class BudgetPostUpdate(BaseModel):
    """Request schema for updating a budget post."""

    category_id: str | None = Field(None, description="Category UUID")
    name: str | None = Field(None, min_length=1, max_length=255)
    type: BudgetPostType | None = Field(None, description="Budget post type: fixed, ceiling, rolling")
    amount_min: int | None = Field(None, ge=0, description="Minimum amount in øre")
    amount_max: int | None = Field(None, ge=0, description="Maximum amount in øre")
    from_account_ids: list[str] | None = Field(None, description="List of account UUIDs (source)")
    to_account_ids: list[str] | None = Field(None, description="List of account UUIDs (destination)")
    recurrence_pattern: RecurrencePattern | None = Field(None, description="Recurrence configuration")


class BudgetPostResponse(BaseModel):
    """Response schema for a single budget post."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    category_id: str
    name: str
    type: BudgetPostType
    amount_min: int
    amount_max: int | None
    from_account_ids: list[str] | None
    to_account_ids: list[str] | None
    recurrence_pattern: dict | None
    created_at: datetime
    updated_at: datetime


class BudgetPostListResponse(BaseModel):
    """Response schema for budget post list with pagination."""

    data: list[BudgetPostResponse]
    next_cursor: str | None = Field(None, description="Cursor for next page, null if no more items")
