"""Transaction schemas for request/response validation."""

from datetime import date as date_type, datetime
from pydantic import BaseModel, ConfigDict, Field

from api.models.transaction import TransactionStatus


class TransactionCreate(BaseModel):
    """Request schema for creating a transaction."""

    account_id: str = Field(..., description="Account UUID")
    date: date_type = Field(..., description="Transaction date")
    amount: int = Field(..., description="Amount in øre (positive = income, negative = expense)")
    description: str = Field(..., min_length=1, max_length=500)
    is_internal_transfer: bool = Field(False, description="Whether this is an internal transfer")
    counterpart_account_id: str | None = Field(None, description="Counterpart account UUID for internal transfer")


class TransactionUpdate(BaseModel):
    """Request schema for updating a transaction."""

    date: date_type | None = None
    amount: int | None = None
    description: str | None = Field(None, min_length=1, max_length=500)
    status: TransactionStatus | None = None


class TransactionResponse(BaseModel):
    """Response schema for a single transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    account_name: str | None = None
    date: date_type
    amount: int
    description: str
    status: TransactionStatus
    is_internal_transfer: bool
    counterpart_transaction_id: str | None
    external_id: str | None
    import_hash: str | None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    """Response schema for transaction list with pagination."""

    data: list[TransactionResponse]
    next_cursor: str | None = Field(None, description="Cursor for next page, null if no more items")


class AllocationItem(BaseModel):
    """Schema for a single allocation item in the request."""

    budget_post_id: str = Field(..., description="Budget post UUID to allocate to")
    amount: int | None = Field(None, description="Amount in øre (null if is_remainder is true)")
    is_remainder: bool = Field(False, description="Whether this allocation receives the remainder")


class AllocationRequest(BaseModel):
    """Request schema for allocating a transaction to budget posts."""

    allocations: list[AllocationItem] = Field(..., description="List of allocations")


class AllocationItemResponse(BaseModel):
    """Response schema for a single allocation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_id: str
    budget_post_id: str
    amount: int
    is_remainder: bool
    created_at: datetime
    updated_at: datetime


class AllocationResponse(BaseModel):
    """Response schema for allocation operation."""

    data: list[AllocationItemResponse]
