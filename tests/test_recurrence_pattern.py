"""Tests for RecurrencePattern schema validation."""

import pytest
from pydantic import ValidationError

from api.schemas.budget_post import (
    RecurrencePattern,
    RecurrenceType,
    RelativePosition,
    AmountPatternCreate,
)


class TestRecurrencePatternOnce:
    """Test validation for 'once' recurrence type."""

    def test_once_valid(self):
        """Valid once recurrence without date field."""
        pattern = RecurrencePattern(type=RecurrenceType.ONCE)
        assert pattern.type == RecurrenceType.ONCE
        assert pattern.interval == 1

    def test_once_with_postpone_weekend(self):
        """Valid once recurrence with postpone_weekend option."""
        pattern = RecurrencePattern(
            type=RecurrenceType.ONCE,
            postpone_weekend=True
        )
        assert pattern.type == RecurrenceType.ONCE
        assert pattern.postpone_weekend is True


class TestRecurrencePatternDaily:
    """Test validation for 'daily' recurrence type."""

    def test_daily_valid(self):
        """Valid daily recurrence."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY)
        assert pattern.type == RecurrenceType.DAILY
        assert pattern.interval == 1

    def test_daily_with_interval(self):
        """Daily recurrence with custom interval (every N days)."""
        pattern = RecurrencePattern(
            type=RecurrenceType.DAILY,
            interval=3
        )
        assert pattern.type == RecurrenceType.DAILY
        assert pattern.interval == 3

    def test_daily_invalid_interval_zero(self):
        """Interval must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.DAILY,
                interval=0
            )
        assert "greater than or equal to 1" in str(exc_info.value)


class TestRecurrencePatternWeekly:
    """Test validation for 'weekly' recurrence type."""

    def test_weekly_valid(self):
        """Valid weekly recurrence on Friday."""
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            weekday=4  # Friday
        )
        assert pattern.type == RecurrenceType.WEEKLY
        assert pattern.weekday == 4
        assert pattern.interval == 1

    def test_weekly_with_interval(self):
        """Weekly recurrence every 2 weeks."""
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            weekday=0,  # Monday
            interval=2
        )
        assert pattern.interval == 2
        assert pattern.weekday == 0

    def test_weekly_missing_weekday(self):
        """Weekly type requires weekday field."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(type=RecurrenceType.WEEKLY)
        assert "'weekly' type requires 'weekday' field" in str(exc_info.value)

    def test_weekly_invalid_weekday(self):
        """Weekday must be 0-6."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.WEEKLY,
                weekday=7  # Invalid
            )
        assert "less than or equal to 6" in str(exc_info.value)


class TestRecurrencePatternMonthlyFixed:
    """Test validation for 'monthly_fixed' recurrence type."""

    def test_monthly_fixed_valid(self):
        """Valid monthly fixed on day 1."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=1
        )
        assert pattern.type == RecurrenceType.MONTHLY_FIXED
        assert pattern.day_of_month == 1

    def test_monthly_fixed_last_day(self):
        """Valid monthly fixed on day 31."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=31
        )
        assert pattern.day_of_month == 31

    def test_monthly_fixed_with_interval(self):
        """Monthly fixed every 3 months."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=15,
            interval=3
        )
        assert pattern.interval == 3

    def test_monthly_fixed_missing_day(self):
        """Monthly fixed requires day_of_month."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(type=RecurrenceType.MONTHLY_FIXED)
        assert "'monthly_fixed' type requires 'day_of_month' field" in str(exc_info.value)

    def test_monthly_fixed_invalid_day(self):
        """Day of month must be 1-31."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.MONTHLY_FIXED,
                day_of_month=32  # Invalid
            )
        assert "less than or equal to 31" in str(exc_info.value)


class TestRecurrencePatternMonthlyRelative:
    """Test validation for 'monthly_relative' recurrence type."""

    def test_monthly_relative_last_weekday(self):
        """Last business day (Friday) of month."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_RELATIVE,
            weekday=4,  # Friday
            relative_position=RelativePosition.LAST
        )
        assert pattern.type == RecurrenceType.MONTHLY_RELATIVE
        assert pattern.weekday == 4
        assert pattern.relative_position == RelativePosition.LAST

    def test_monthly_relative_first_monday(self):
        """First Monday of month."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_RELATIVE,
            weekday=0,  # Monday
            relative_position=RelativePosition.FIRST
        )
        assert pattern.relative_position == RelativePosition.FIRST

    def test_monthly_relative_missing_weekday(self):
        """Monthly relative requires weekday."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.MONTHLY_RELATIVE,
                relative_position=RelativePosition.LAST
            )
        assert "'monthly_relative' type requires 'weekday' field" in str(exc_info.value)

    def test_monthly_relative_missing_position(self):
        """Monthly relative requires relative_position."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.MONTHLY_RELATIVE,
                weekday=4
            )
        assert "'monthly_relative' type requires 'relative_position' field" in str(exc_info.value)


class TestRecurrencePatternYearly:
    """Test validation for 'yearly' recurrence type."""

    def test_yearly_fixed_date(self):
        """Yearly on June 15."""
        pattern = RecurrencePattern(
            type=RecurrenceType.YEARLY,
            month=6,
            day_of_month=15
        )
        assert pattern.type == RecurrenceType.YEARLY
        assert pattern.month == 6
        assert pattern.day_of_month == 15

    def test_yearly_relative_date(self):
        """Yearly on last Friday of December."""
        pattern = RecurrencePattern(
            type=RecurrenceType.YEARLY,
            month=12,
            weekday=4,
            relative_position=RelativePosition.LAST
        )
        assert pattern.month == 12
        assert pattern.weekday == 4
        assert pattern.relative_position == RelativePosition.LAST

    def test_yearly_with_interval(self):
        """Yearly every 2 years."""
        pattern = RecurrencePattern(
            type=RecurrenceType.YEARLY,
            month=6,
            day_of_month=1,
            interval=2
        )
        assert pattern.interval == 2

    def test_yearly_missing_month(self):
        """Yearly requires month field."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.YEARLY,
                day_of_month=15
            )
        assert "'yearly' type requires 'month' field" in str(exc_info.value)

    def test_yearly_missing_both_day_and_relative(self):
        """Yearly requires either day_of_month or relative_position+weekday."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.YEARLY,
                month=6
            )
        assert "'yearly' type requires either 'day_of_month' OR ('relative_position' + 'weekday')" in str(exc_info.value)

    def test_yearly_both_day_and_relative(self):
        """Yearly cannot have both day_of_month and relative_position."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.YEARLY,
                month=6,
                day_of_month=15,
                weekday=4,
                relative_position=RelativePosition.LAST
            )
        assert "'yearly' type cannot have both 'day_of_month' and 'relative_position'" in str(exc_info.value)

    def test_yearly_relative_missing_weekday(self):
        """Yearly relative requires weekday."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.YEARLY,
                month=6,
                relative_position=RelativePosition.LAST
            )
        assert "'yearly' type requires either 'day_of_month' OR ('relative_position' + 'weekday')" in str(exc_info.value)


class TestRecurrencePatternPeriodOnce:
    """Test validation for 'period_once' recurrence type."""

    def test_period_once_valid(self):
        """Period once without months field."""
        pattern = RecurrencePattern(type=RecurrenceType.PERIOD_ONCE)
        assert pattern.type == RecurrenceType.PERIOD_ONCE


class TestRecurrencePatternPeriodMonthly:
    """Test validation for 'period_monthly' recurrence type."""

    def test_period_monthly_valid(self):
        """Period monthly with default interval."""
        pattern = RecurrencePattern(type=RecurrenceType.PERIOD_MONTHLY)
        assert pattern.type == RecurrenceType.PERIOD_MONTHLY
        assert pattern.interval == 1

    def test_period_monthly_with_interval(self):
        """Period monthly with custom interval (e.g. 3 for quarterly)."""
        pattern = RecurrencePattern(
            type=RecurrenceType.PERIOD_MONTHLY,
            interval=3
        )
        assert pattern.interval == 3

    def test_period_monthly_no_months_field_required(self):
        """Period monthly does not require months field."""
        pattern = RecurrencePattern(type=RecurrenceType.PERIOD_MONTHLY)
        assert pattern.months is None


class TestRecurrencePatternPeriodYearly:
    """Test validation for 'period_yearly' recurrence type."""

    def test_period_yearly_quarterly(self):
        """Period yearly quarterly (mar, jun, sep, dec)."""
        pattern = RecurrencePattern(
            type=RecurrenceType.PERIOD_YEARLY,
            months=[3, 6, 9, 12]
        )
        assert pattern.type == RecurrenceType.PERIOD_YEARLY
        assert pattern.months == [3, 6, 9, 12]

    def test_period_yearly_with_interval(self):
        """Period yearly every 2 years."""
        pattern = RecurrencePattern(
            type=RecurrenceType.PERIOD_YEARLY,
            months=[1],
            interval=2
        )
        assert pattern.interval == 2

    def test_period_yearly_missing_months(self):
        """Period yearly requires months list."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(type=RecurrenceType.PERIOD_YEARLY)
        assert "'period_yearly' type requires non-empty 'months' list" in str(exc_info.value)


class TestRecurrencePatternMonthsValidation:
    """Test months field validation."""

    def test_months_invalid_value(self):
        """Months must be 1-12."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.PERIOD_YEARLY,
                months=[1, 13]  # 13 is invalid
            )
        assert "All months must be between 1 and 12" in str(exc_info.value)

    def test_months_duplicate_values(self):
        """Months must be unique."""
        with pytest.raises(ValidationError) as exc_info:
            RecurrencePattern(
                type=RecurrenceType.PERIOD_YEARLY,
                months=[1, 2, 2, 3]  # Duplicate 2
            )
        assert "Months must be unique" in str(exc_info.value)


class TestRecurrencePatternPostponeWeekend:
    """Test postpone_weekend option."""

    def test_postpone_weekend_default_false(self):
        """Default postpone_weekend is False."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=1
        )
        assert pattern.postpone_weekend is False

    def test_postpone_weekend_explicit_true(self):
        """Can set postpone_weekend to True."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=1,
            postpone_weekend=True
        )
        assert pattern.postpone_weekend is True

    def test_postpone_weekend_with_various_types(self):
        """Postpone weekend works with date-based types."""
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            weekday=4,
            postpone_weekend=True
        )
        assert pattern.postpone_weekend is True


class TestRecurrencePatternExamples:
    """Test real-world examples from spec."""

    def test_example_salary_last_business_day(self):
        """Løn: Sidste hverdag i måneden."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_RELATIVE,
            weekday=4,  # Friday
            relative_position=RelativePosition.LAST
        )
        assert pattern.type == RecurrenceType.MONTHLY_RELATIVE

    def test_example_rent_first_with_postpone(self):
        """Husleje: D. 1. hver måned (eller næste hverdag)."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY_FIXED,
            day_of_month=1,
            postpone_weekend=True
        )
        assert pattern.day_of_month == 1
        assert pattern.postpone_weekend is True

    def test_example_savings_every_friday(self):
        """Børneopsparing: Hver fredag."""
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            weekday=4  # Friday
        )
        assert pattern.type == RecurrenceType.WEEKLY
        assert pattern.weekday == 4

    def test_example_insurance_quarterly(self):
        """Forsikring: Kvartalsvis."""
        pattern = RecurrencePattern(
            type=RecurrenceType.PERIOD_YEARLY,
            months=[3, 6, 9, 12]
        )
        assert pattern.months == [3, 6, 9, 12]

    def test_example_electricity_summer(self):
        """El-regning (sommer): Jun-Sep."""
        pattern = RecurrencePattern(
            type=RecurrenceType.PERIOD_YEARLY,
            months=[6, 7, 8, 9]
        )
        assert pattern.months == [6, 7, 8, 9]


class TestAmountPatternEndDateValidation:
    """Test end_date validation for non-repeating recurrence types."""

    def test_once_with_end_date_invalid(self):
        """AmountPattern with once recurrence cannot have end_date."""
        with pytest.raises(ValidationError) as exc_info:
            AmountPatternCreate(
                amount=10000,
                start_date="2026-03-15",
                end_date="2026-12-31",
                recurrence_pattern=RecurrencePattern(type=RecurrenceType.ONCE)
            )
        assert "end_date must be null for non-repeating types" in str(exc_info.value)

    def test_once_without_end_date_valid(self):
        """AmountPattern with once recurrence and null end_date is valid."""
        pattern = AmountPatternCreate(
            amount=10000,
            start_date="2026-03-15",
            end_date=None,
            recurrence_pattern=RecurrencePattern(type=RecurrenceType.ONCE)
        )
        assert pattern.amount == 10000
        assert pattern.end_date is None

    def test_period_once_with_end_date_invalid(self):
        """AmountPattern with period_once recurrence cannot have end_date."""
        with pytest.raises(ValidationError) as exc_info:
            AmountPatternCreate(
                amount=50000,
                start_date="2026-06-01",
                end_date="2026-12-31",
                recurrence_pattern=RecurrencePattern(type=RecurrenceType.PERIOD_ONCE)
            )
        assert "end_date must be null for non-repeating types" in str(exc_info.value)

    def test_period_once_without_end_date_valid(self):
        """AmountPattern with period_once recurrence and null end_date is valid."""
        pattern = AmountPatternCreate(
            amount=50000,
            start_date="2026-06-01",
            end_date=None,
            recurrence_pattern=RecurrencePattern(type=RecurrenceType.PERIOD_ONCE)
        )
        assert pattern.amount == 50000
        assert pattern.end_date is None

    def test_repeating_type_with_end_date_valid(self):
        """AmountPattern with repeating recurrence can have end_date."""
        pattern = AmountPatternCreate(
            amount=10000,
            start_date="2026-01-01",
            end_date="2026-12-31",
            recurrence_pattern=RecurrencePattern(
                type=RecurrenceType.MONTHLY_FIXED,
                day_of_month=1
            )
        )
        assert pattern.end_date == "2026-12-31"

    def test_period_monthly_with_end_date_valid(self):
        """AmountPattern with period_monthly recurrence can have end_date."""
        pattern = AmountPatternCreate(
            amount=20000,
            start_date="2026-01-01",
            end_date="2026-06-30",
            recurrence_pattern=RecurrencePattern(type=RecurrenceType.PERIOD_MONTHLY)
        )
        assert pattern.end_date == "2026-06-30"
