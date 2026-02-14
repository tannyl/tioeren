"""Account schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from api.models.account import AccountPurpose, AccountDatasource
from api.schemas import MAX_BIGINT


class AccountCreate(BaseModel):
    """Request schema for creating an account."""

    name: str = Field(..., min_length=1, max_length=255)
    purpose: AccountPurpose
    datasource: AccountDatasource
    currency: str = Field("DKK", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    starting_balance: int = Field(..., ge=-MAX_BIGINT, le=MAX_BIGINT, description="Starting balance in øre (smallest currency unit)")
    can_go_negative: bool | None = Field(None, description="Whether account can have negative balance")
    needs_coverage: bool | None = Field(None, description="Whether negative balance must be covered")


class AccountUpdate(BaseModel):
    """Request schema for updating an account."""

    name: str | None = Field(None, min_length=1, max_length=255)
    purpose: AccountPurpose | None = None
    datasource: AccountDatasource | None = None
    currency: str | None = Field(None, min_length=3, max_length=3, description="Currency code (ISO 4217)")
    starting_balance: int | None = Field(None, ge=-MAX_BIGINT, le=MAX_BIGINT, description="Starting balance in øre")
    can_go_negative: bool | None = None
    needs_coverage: bool | None = None


class AccountResponse(BaseModel):
    """Response schema for a single account."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    name: str
    purpose: AccountPurpose
    datasource: AccountDatasource
    currency: str
    starting_balance: int
    can_go_negative: bool
    needs_coverage: bool
    current_balance: int
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    """Response schema for account list."""

    data: list[AccountResponse]
