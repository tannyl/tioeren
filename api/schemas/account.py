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
    credit_limit: int | None = Field(None, ge=-MAX_BIGINT, le=MAX_BIGINT, description="Credit limit in øre (0 = cannot go negative, None = no limit)")
    locked: bool = Field(False, description="Whether account is locked (only for savings accounts)")


class AccountUpdate(BaseModel):
    """Request schema for updating an account."""

    name: str | None = Field(None, min_length=1, max_length=255)
    purpose: AccountPurpose | None = None
    datasource: AccountDatasource | None = None
    currency: str | None = Field(None, min_length=3, max_length=3, description="Currency code (ISO 4217)")
    starting_balance: int | None = Field(None, ge=-MAX_BIGINT, le=MAX_BIGINT, description="Starting balance in øre")
    credit_limit: int | None = Field(None, ge=-MAX_BIGINT, le=MAX_BIGINT, description="Credit limit in øre")
    locked: bool | None = None


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
    credit_limit: int | None
    locked: bool
    current_balance: int
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    """Response schema for account list."""

    data: list[AccountResponse]
