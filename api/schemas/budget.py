"""Budget schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import MAX_BIGINT


class BudgetCreate(BaseModel):
    """Request schema for creating a budget."""

    name: str = Field(..., min_length=1, max_length=255)
    currency: str = Field("DKK", min_length=3, max_length=3, description="Currency code (ISO 4217, e.g., DKK)")
    warning_threshold: int | None = Field(None, ge=0, le=MAX_BIGINT, description="Warning threshold in øre")


class BudgetUpdate(BaseModel):
    """Request schema for updating a budget."""

    name: str | None = Field(None, min_length=1, max_length=255)
    currency: str | None = Field(None, min_length=3, max_length=3, description="Currency code (ISO 4217)")
    warning_threshold: int | None = Field(None, ge=0, le=MAX_BIGINT, description="Warning threshold in øre")


class BudgetResponse(BaseModel):
    """Response schema for a single budget."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    currency: str
    owner_id: str
    warning_threshold: int | None
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    """Response schema for budget list with pagination."""

    data: list[BudgetResponse]
    next_cursor: str | None = Field(None, description="Cursor for next page, null if no more items")
