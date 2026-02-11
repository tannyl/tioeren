"""Budget post schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.models.budget_post import BudgetPostType


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
    - period_yearly: Every N year in specific months
    """

    type: RecurrenceType = Field(..., description="Recurrence type")

    # Interval - how often (every N days/weeks/months/years)
    interval: int = Field(1, ge=1, description="Interval: every N days/weeks/months/years")

    # Date-based fields
    date: str | None = Field(None, description="ISO date for 'once' type (YYYY-MM-DD)")
    weekday: int | None = Field(None, ge=0, le=6, description="Weekday (0=Monday, 6=Sunday) for weekly/monthly_relative")
    day_of_month: int | None = Field(None, ge=1, le=31, description="Day of month for monthly_fixed/yearly")
    relative_position: RelativePosition | None = Field(None, description="Position for monthly_relative/yearly (first/last)")
    month: int | None = Field(None, ge=1, le=12, description="Month (1-12) for yearly")

    # Period-based fields
    months: list[int] | None = Field(None, description="Months (1-12) for period_once/period_yearly")

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
            if not self.date:
                raise ValueError("'once' type requires 'date' field")
            # Validate date format
            try:
                datetime.fromisoformat(self.date)
            except ValueError:
                raise ValueError("'date' must be valid ISO date format (YYYY-MM-DD)")

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
            if not self.months or len(self.months) == 0:
                raise ValueError("'period_once' type requires non-empty 'months' list")

        elif type_val == RecurrenceType.PERIOD_YEARLY:
            if not self.months or len(self.months) == 0:
                raise ValueError("'period_yearly' type requires non-empty 'months' list")

        return self


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
