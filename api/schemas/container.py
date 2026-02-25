"""Container schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.models.container import ContainerType
from api.schemas import MAX_BIGINT


class ContainerCreate(BaseModel):
    """Request schema for creating a container."""

    name: str = Field(..., min_length=1, max_length=255)
    type: ContainerType
    starting_balance: int = Field(..., ge=-MAX_BIGINT, le=MAX_BIGINT, description="Starting balance in øre (smallest currency unit)")
    bank_name: str | None = Field(None, description="Bank name (optional)")
    bank_account_name: str | None = Field(None, description="Bank account name (optional)")
    bank_reg_number: str | None = Field(None, description="Bank registration number (optional)")
    bank_account_number: str | None = Field(None, description="Bank account number (optional)")
    overdraft_limit: int | None = Field(None, le=0, ge=-MAX_BIGINT, description="Overdraft limit in øre (cashbox only, negative floor)")
    locked: bool | None = Field(None, description="Whether container is locked (piggybank only)")
    credit_limit: int | None = Field(None, le=0, ge=-MAX_BIGINT, description="Credit limit in øre (debt only, REQUIRED for debt, negative floor)")
    allow_withdrawals: bool | None = Field(None, description="Whether withdrawals are allowed (debt only)")
    interest_rate: float | None = Field(None, gt=0, description="Annual interest rate percentage (debt only, must be > 0)")
    interest_frequency: str | None = Field(None, description="Interest frequency: monthly, quarterly, or yearly (debt only)")
    required_payment: int | None = Field(None, gt=0, le=MAX_BIGINT, description="Required payment amount in øre (debt only, must be > 0)")

    @model_validator(mode="after")
    def validate_type_constraints(self):
        """Validate type-specific field constraints."""
        container_type = self.type

        if container_type == ContainerType.CASHBOX:
            # Cashbox: MUST NOT have debt/piggybank fields
            if self.credit_limit is not None:
                raise ValueError("cashbox containers cannot have credit_limit")
            if self.allow_withdrawals is not None:
                raise ValueError("cashbox containers cannot have allow_withdrawals")
            if self.interest_rate is not None:
                raise ValueError("cashbox containers cannot have interest_rate")
            if self.interest_frequency is not None:
                raise ValueError("cashbox containers cannot have interest_frequency")
            if self.required_payment is not None:
                raise ValueError("cashbox containers cannot have required_payment")
            if self.locked is not None:
                raise ValueError("cashbox containers cannot have locked")
            # overdraft_limit is allowed and validated by Field constraint (le=0)

        elif container_type == ContainerType.PIGGYBANK:
            # Piggybank: MUST NOT have cashbox/debt fields
            if self.overdraft_limit is not None:
                raise ValueError("piggybank containers cannot have overdraft_limit")
            if self.credit_limit is not None:
                raise ValueError("piggybank containers cannot have credit_limit")
            if self.allow_withdrawals is not None:
                raise ValueError("piggybank containers cannot have allow_withdrawals")
            if self.interest_rate is not None:
                raise ValueError("piggybank containers cannot have interest_rate")
            if self.interest_frequency is not None:
                raise ValueError("piggybank containers cannot have interest_frequency")
            if self.required_payment is not None:
                raise ValueError("piggybank containers cannot have required_payment")
            # locked is allowed

        elif container_type == ContainerType.DEBT:
            # Debt: MUST NOT have cashbox/piggybank fields
            if self.overdraft_limit is not None:
                raise ValueError("debt containers cannot have overdraft_limit")
            if self.locked is not None:
                raise ValueError("debt containers cannot have locked")

            # Debt: credit_limit is REQUIRED
            if self.credit_limit is None:
                raise ValueError("debt containers MUST have credit_limit (negative floor)")

            # Debt: interest_frequency must be valid if provided
            if self.interest_frequency is not None:
                valid_frequencies = ["monthly", "quarterly", "yearly"]
                if self.interest_frequency not in valid_frequencies:
                    raise ValueError(f"interest_frequency must be one of: {', '.join(valid_frequencies)}")

            # interest_rate, allow_withdrawals, required_payment are optional for debt
            # Field validators already enforce: interest_rate > 0, required_payment > 0

        return self


class ContainerUpdate(BaseModel):
    """Request schema for updating a container."""

    name: str | None = Field(None, min_length=1, max_length=255)
    type: ContainerType | None = None
    starting_balance: int | None = Field(None, ge=-MAX_BIGINT, le=MAX_BIGINT, description="Starting balance in øre")
    bank_name: str | None = None
    bank_account_name: str | None = None
    bank_reg_number: str | None = None
    bank_account_number: str | None = None
    overdraft_limit: int | None = Field(None, le=0, ge=-MAX_BIGINT, description="Overdraft limit in øre (cashbox only, negative floor)")
    locked: bool | None = None
    credit_limit: int | None = Field(None, le=0, ge=-MAX_BIGINT, description="Credit limit in øre (debt only, negative floor)")
    allow_withdrawals: bool | None = None
    interest_rate: float | None = Field(None, gt=0, description="Annual interest rate percentage (debt only, must be > 0)")
    interest_frequency: str | None = None
    required_payment: int | None = Field(None, gt=0, le=MAX_BIGINT, description="Required payment amount in øre (debt only, must be > 0)")

    @model_validator(mode="after")
    def validate_type_constraints(self):
        """Validate type-specific field constraints for updates."""
        # Note: For updates, we can't fully validate type constraints without knowing
        # the existing container type. The service layer will need to handle this.
        # Here we just validate field value constraints.

        # If interest_frequency is provided, validate it
        if self.interest_frequency is not None:
            valid_frequencies = ["monthly", "quarterly", "yearly"]
            if self.interest_frequency not in valid_frequencies:
                raise ValueError(f"interest_frequency must be one of: {', '.join(valid_frequencies)}")

        return self


class ContainerResponse(BaseModel):
    """Response schema for a single container."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    name: str
    type: ContainerType
    starting_balance: int
    bank_name: str | None
    bank_account_name: str | None
    bank_reg_number: str | None
    bank_account_number: str | None
    overdraft_limit: int | None
    locked: bool | None
    credit_limit: int | None
    allow_withdrawals: bool | None
    interest_rate: float | None
    interest_frequency: str | None
    required_payment: int | None
    current_balance: int
    created_at: datetime
    updated_at: datetime


class ContainerListResponse(BaseModel):
    """Response schema for container list."""

    data: list[ContainerResponse]
