"""Budget post schemas for request/response validation."""

from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.models.budget_post import BudgetPostType, BudgetPostDirection, CounterpartyType
from api.schemas import MAX_BIGINT


class RecurrenceType(str, Enum):
    """Recurrence pattern types."""

    # Date-based recurrence (specific dates)
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY_FIXED = "monthly_fixed"
    MONTHLY_RELATIVE = "monthly_relative"
    YEARLY = "yearly"

    # Period-based recurrence (budget periods/months)
    PERIOD_ONCE = "period_once"
    PERIOD_MONTHLY = "period_monthly"
    PERIOD_YEARLY = "period_yearly"


class RelativePosition(str, Enum):
    """Position for relative monthly/yearly recurrence."""

    FIRST = "first"
    LAST = "last"


class RecurrencePattern(BaseModel):
    """Schema for recurrence pattern configuration.

    Date-based recurrence: transactions on specific dates
    - once: One specific date
    - daily: Every N day from start date
    - weekly: Every N week on specific weekday
    - monthly_fixed: Every N month on specific day (1-31)
    - monthly_relative: Every N month on first/last weekday
    - yearly: Every N year in specific month on day or relative

    Period-based recurrence: budgets applying to periods (months)
    - period_once: In specific months
    - period_monthly: Every N month from start date
    - period_yearly: Every N year in specific months
    """

    type: RecurrenceType = Field(..., description="Recurrence type")

    # Interval - how often (every N days/weeks/months/years)
    interval: int = Field(1, ge=1, description="Interval: every N days/weeks/months/years")

    # Date-based fields
    weekday: int | None = Field(None, ge=0, le=6, description="Weekday (0=Monday, 6=Sunday) for weekly/monthly_relative")
    day_of_month: int | None = Field(None, ge=1, le=31, description="Day of month for monthly_fixed/yearly")
    relative_position: RelativePosition | None = Field(None, description="Position for monthly_relative/yearly (first/last)")
    month: int | None = Field(None, ge=1, le=12, description="Month (1-12) for yearly")

    # Period-based fields
    months: list[int] | None = Field(None, description="Months (1-12) for period_yearly")

    # Options
    postpone_weekend: bool = Field(False, description="Postpone to next business day if weekend/holiday")

    @field_validator("months")
    @classmethod
    def validate_months(cls, v: list[int] | None) -> list[int] | None:
        """Validate months are in range 1-12 and unique."""
        if v is not None:
            if not all(1 <= month <= 12 for month in v):
                raise ValueError("All months must be between 1 and 12")
            if len(v) != len(set(v)):
                raise ValueError("Months must be unique")
        return v

    @model_validator(mode="after")
    def validate_recurrence_fields(self) -> "RecurrencePattern":
        """Validate that required fields are present based on recurrence type."""
        type_val = self.type

        # Date-based validations
        if type_val == RecurrenceType.ONCE:
            # No additional fields required - start_date on AmountPattern determines the occurrence
            pass

        elif type_val == RecurrenceType.DAILY:
            # No additional required fields, interval is enough
            pass

        elif type_val == RecurrenceType.WEEKLY:
            if self.weekday is None:
                raise ValueError("'weekly' type requires 'weekday' field (0=Monday, 6=Sunday)")

        elif type_val == RecurrenceType.MONTHLY_FIXED:
            if self.day_of_month is None:
                raise ValueError("'monthly_fixed' type requires 'day_of_month' field (1-31)")

        elif type_val == RecurrenceType.MONTHLY_RELATIVE:
            if self.weekday is None:
                raise ValueError("'monthly_relative' type requires 'weekday' field (0=Monday, 6=Sunday)")
            if self.relative_position is None:
                raise ValueError("'monthly_relative' type requires 'relative_position' field (first/last)")

        elif type_val == RecurrenceType.YEARLY:
            if self.month is None:
                raise ValueError("'yearly' type requires 'month' field (1-12)")
            # Must have either day_of_month OR (relative_position + weekday)
            has_fixed = self.day_of_month is not None
            has_relative = self.relative_position is not None and self.weekday is not None
            if not has_fixed and not has_relative:
                raise ValueError("'yearly' type requires either 'day_of_month' OR ('relative_position' + 'weekday')")
            if has_fixed and has_relative:
                raise ValueError("'yearly' type cannot have both 'day_of_month' and 'relative_position'")

        # Period-based validations
        elif type_val == RecurrenceType.PERIOD_ONCE:
            # No additional fields required - start_date on AmountPattern determines year+month
            pass

        elif type_val == RecurrenceType.PERIOD_MONTHLY:
            # No additional fields required - just type + optional interval
            pass

        elif type_val == RecurrenceType.PERIOD_YEARLY:
            if not self.months or len(self.months) == 0:
                raise ValueError("'period_yearly' type requires non-empty 'months' list")

        return self


class AmountPatternCreate(BaseModel):
    """Request schema for creating an amount pattern."""

    amount: int = Field(..., ge=0, le=MAX_BIGINT, description="Amount in øre")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD), null = indefinite")
    recurrence_pattern: RecurrencePattern | None = Field(None, description="Recurrence configuration")
    account_ids: list[str] | None = Field(None, description="NORMAL account UUIDs for this pattern")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate date is in ISO format."""
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be valid ISO date format (YYYY-MM-DD)")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "AmountPatternCreate":
        """Validate end_date is after start_date if both provided."""
        if self.end_date is not None and self.start_date is not None:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)
            if end < start:
                raise ValueError("end_date must be on or after start_date")
        return self

    @model_validator(mode="after")
    def validate_non_repeating_end_date(self) -> "AmountPatternCreate":
        """Non-repeating types must have null end_date."""
        if self.recurrence_pattern is not None:
            if self.recurrence_pattern.type in (RecurrenceType.ONCE, RecurrenceType.PERIOD_ONCE):
                if self.end_date is not None:
                    raise ValueError("end_date must be null for non-repeating types (once, period_once)")
        return self


class AmountPatternUpdate(BaseModel):
    """Request schema for updating an amount pattern."""

    amount: int | None = Field(None, ge=0, le=MAX_BIGINT, description="Amount in øre")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD), null = indefinite")
    recurrence_pattern: RecurrencePattern | None = Field(None, description="Recurrence configuration")
    account_ids: list[str] | None = Field(None, description="NORMAL account UUIDs for this pattern")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate date is in ISO format."""
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be valid ISO date format (YYYY-MM-DD)")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "AmountPatternUpdate":
        """Validate end_date is after start_date when both provided."""
        if self.end_date is not None and self.start_date is not None:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)
            if end < start:
                raise ValueError("end_date must be on or after start_date")
        return self


class AmountPatternResponse(BaseModel):
    """Response schema for an amount pattern."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_post_id: str
    amount: int
    start_date: str
    end_date: str | None
    recurrence_pattern: dict | None
    account_ids: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class BudgetPostCreate(BaseModel):
    """Request schema for creating a budget post."""

    direction: BudgetPostDirection = Field(..., description="Direction: income, expense, transfer")
    category_id: str | None = Field(None, description="Category UUID (required for income/expense, null for transfer)")
    type: BudgetPostType = Field(..., description="Budget post type: fixed, ceiling")
    accumulate: bool = Field(False, description="Accumulate unused amounts (only for ceiling type)")
    counterparty_type: CounterpartyType | None = Field(None, description="Counterparty type: external, account (null for transfer)")
    counterparty_account_id: str | None = Field(None, description="Counterparty account UUID (only if counterparty_type=account)")
    transfer_from_account_id: str | None = Field(None, description="Transfer from account UUID (only for transfer)")
    transfer_to_account_id: str | None = Field(None, description="Transfer to account UUID (only for transfer)")
    amount_patterns: list[AmountPatternCreate] = Field(..., min_length=1, description="Amount patterns (at least one required)")

    @field_validator("amount_patterns")
    @classmethod
    def validate_amount_patterns(cls, v: list[AmountPatternCreate]) -> list[AmountPatternCreate]:
        """Validate that at least one amount pattern is provided."""
        if not v or len(v) == 0:
            raise ValueError("At least one amount pattern is required")
        return v


class BudgetPostUpdate(BaseModel):
    """Request schema for updating a budget post."""

    type: BudgetPostType | None = Field(None, description="Budget post type: fixed, ceiling")
    accumulate: bool | None = Field(None, description="Accumulate unused amounts (only for ceiling type)")
    counterparty_type: CounterpartyType | None = Field(None, description="Counterparty type: external, account")
    counterparty_account_id: str | None = Field(None, description="Counterparty account UUID")
    transfer_from_account_id: str | None = Field(None, description="Transfer from account UUID")
    transfer_to_account_id: str | None = Field(None, description="Transfer to account UUID")
    amount_patterns: list[AmountPatternCreate] | None = Field(None, description="Amount patterns (replaces existing patterns)")


class BudgetPostResponse(BaseModel):
    """Response schema for a single budget post."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    direction: BudgetPostDirection
    category_id: str | None
    category_name: str | None
    type: BudgetPostType
    accumulate: bool
    counterparty_type: CounterpartyType | None
    counterparty_account_id: str | None
    transfer_from_account_id: str | None
    transfer_to_account_id: str | None
    amount_patterns: list[AmountPatternResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BudgetPostListResponse(BaseModel):
    """Response schema for budget post list with pagination."""

    data: list[BudgetPostResponse]
    next_cursor: str | None = Field(None, description="Cursor for next page, null if no more items")


class OccurrenceResponse(BaseModel):
    """Response schema for a single occurrence."""

    date: str = Field(..., description="Occurrence date (YYYY-MM-DD)")
    amount: int = Field(..., description="Expected amount in øre")


class BudgetPostOccurrencesResponse(BaseModel):
    """Response schema for budget post occurrences."""

    budget_post_id: str
    occurrences: list[OccurrenceResponse]


class BulkOccurrencesResponse(BaseModel):
    """Response schema for bulk occurrences across multiple budget posts."""

    data: list[BudgetPostOccurrencesResponse]


class AmountOccurrenceResponse(BaseModel):
    """Response schema for an amount occurrence."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    archived_budget_post_id: str
    date: str | None
    amount: int
    created_at: datetime


class ArchivedBudgetPostResponse(BaseModel):
    """Response schema for an archived budget post."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    budget_post_id: str | None
    period_year: int
    period_month: int
    direction: BudgetPostDirection
    category_id: str | None
    category_name: str | None = None
    type: BudgetPostType
    amount_occurrences: list[AmountOccurrenceResponse] = Field(default_factory=list)
    created_at: datetime


class ArchivedBudgetPostListResponse(BaseModel):
    """Response schema for archived budget post list."""
    data: list[ArchivedBudgetPostResponse]
