"""Tests for recurrence pattern expansion to concrete occurrence dates."""

import pytest
from datetime import date
from uuid import uuid4

from api.models.budget_post import BudgetPostType
from api.schemas.budget_post import RecurrenceType, RelativePosition
from api.services.budget_post_service import _expand_recurrence_pattern


class TestOccurrenceExpansionOnce:
    """Test occurrence expansion for 'once' recurrence type."""

    def test_once_within_range(self):
        """Single occurrence within range."""
        pattern = {
            "type": RecurrenceType.ONCE.value,
            "date": "2026-02-15"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 15)

    def test_once_before_range(self):
        """Single occurrence before range."""
        pattern = {
            "type": RecurrenceType.ONCE.value,
            "date": "2026-01-15"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_once_after_range(self):
        """Single occurrence after range."""
        pattern = {
            "type": RecurrenceType.ONCE.value,
            "date": "2026-03-15"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_once_on_saturday_with_postpone(self):
        """Occurrence on Saturday postponed to Monday."""
        pattern = {
            "type": RecurrenceType.ONCE.value,
            "date": "2026-02-14",  # Saturday
            "postpone_weekend": True
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 16)  # Monday

    def test_once_on_sunday_with_postpone(self):
        """Occurrence on Sunday postponed to Monday."""
        pattern = {
            "type": RecurrenceType.ONCE.value,
            "date": "2026-02-15",  # Sunday
            "postpone_weekend": True
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 16)  # Monday


class TestOccurrenceExpansionDaily:
    """Test occurrence expansion for 'daily' recurrence type."""

    def test_daily_every_day(self):
        """Daily occurrence every single day."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 7)
        )

        assert len(occurrences) == 7
        assert occurrences[0] == date(2026, 2, 1)
        assert occurrences[6] == date(2026, 2, 7)

    def test_daily_every_3_days(self):
        """Daily occurrence every 3 days."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 3
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 10)
        )

        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 2, 1)
        assert occurrences[1] == date(2026, 2, 4)
        assert occurrences[2] == date(2026, 2, 7)
        assert occurrences[3] == date(2026, 2, 10)


class TestOccurrenceExpansionWeekly:
    """Test occurrence expansion for 'weekly' recurrence type."""

    def test_weekly_every_friday(self):
        """Every Friday in February 2026."""
        pattern = {
            "type": RecurrenceType.WEEKLY.value,
            "weekday": 4,  # Friday
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Fridays in Feb 2026: 6, 13, 20, 27
        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 2, 6)
        assert occurrences[1] == date(2026, 2, 13)
        assert occurrences[2] == date(2026, 2, 20)
        assert occurrences[3] == date(2026, 2, 27)

    def test_weekly_every_other_monday(self):
        """Every other Monday."""
        pattern = {
            "type": RecurrenceType.WEEKLY.value,
            "weekday": 0,  # Monday
            "interval": 2
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),  # Sunday
            date(2026, 2, 28)
        )

        # Mondays in Feb 2026: 2, 9, 16, 23
        # Every other: 2, 16
        assert len(occurrences) == 2
        assert occurrences[0] == date(2026, 2, 2)
        assert occurrences[1] == date(2026, 2, 16)


class TestOccurrenceExpansionMonthlyFixed:
    """Test occurrence expansion for 'monthly_fixed' recurrence type."""

    def test_monthly_first_day(self):
        """First day of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 1,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 1)
        assert occurrences[1] == date(2026, 2, 1)
        assert occurrences[2] == date(2026, 3, 1)

    def test_monthly_15th(self):
        """15th of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 15,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 15)
        assert occurrences[1] == date(2026, 2, 15)
        assert occurrences[2] == date(2026, 3, 15)

    def test_monthly_31st_in_february(self):
        """31st of month handles February correctly."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 31,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Jan has 31 days, Feb has 28, Mar has 31
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 31)
        assert occurrences[1] == date(2026, 2, 28)  # Last day of Feb
        assert occurrences[2] == date(2026, 3, 31)

    def test_monthly_every_3_months(self):
        """Every 3 months on the 15th."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 15,
            "interval": 3
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # Jan, Apr, Jul, Oct
        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 1, 15)
        assert occurrences[1] == date(2026, 4, 15)
        assert occurrences[2] == date(2026, 7, 15)
        assert occurrences[3] == date(2026, 10, 15)

    def test_monthly_with_postpone_on_saturday(self):
        """Monthly on 1st with postpone (Feb 1, 2026 is Sunday)."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 1,
            "interval": 1,
            "postpone_weekend": True
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Feb 1, 2026 is a Sunday, should be postponed to Monday Feb 2
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 2)


class TestOccurrenceExpansionMonthlyRelative:
    """Test occurrence expansion for 'monthly_relative' recurrence type."""

    def test_monthly_first_monday(self):
        """First Monday of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_RELATIVE.value,
            "weekday": 0,  # Monday
            "relative_position": RelativePosition.FIRST.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Jan 5, Feb 2, Mar 2
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 5)
        assert occurrences[1] == date(2026, 2, 2)
        assert occurrences[2] == date(2026, 3, 2)

    def test_monthly_last_friday(self):
        """Last Friday of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_RELATIVE.value,
            "weekday": 4,  # Friday
            "relative_position": RelativePosition.LAST.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Jan 30, Feb 27, Mar 27
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 30)
        assert occurrences[1] == date(2026, 2, 27)
        assert occurrences[2] == date(2026, 3, 27)


class TestOccurrenceExpansionYearly:
    """Test occurrence expansion for 'yearly' recurrence type."""

    def test_yearly_fixed_date(self):
        """Yearly on June 15."""
        pattern = {
            "type": RecurrenceType.YEARLY.value,
            "month": 6,
            "day_of_month": 15,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 1, 1),
            date(2027, 12, 31)
        )

        assert len(occurrences) == 3
        assert occurrences[0] == date(2025, 6, 15)
        assert occurrences[1] == date(2026, 6, 15)
        assert occurrences[2] == date(2027, 6, 15)

    def test_yearly_relative_date(self):
        """Yearly on last Friday of December."""
        pattern = {
            "type": RecurrenceType.YEARLY.value,
            "month": 12,
            "weekday": 4,  # Friday
            "relative_position": RelativePosition.LAST.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 1, 1),
            date(2027, 12, 31)
        )

        # Last Friday in Dec: 2025-12-26, 2026-12-25, 2027-12-31
        assert len(occurrences) == 3
        assert occurrences[0] == date(2025, 12, 26)
        assert occurrences[1] == date(2026, 12, 25)
        assert occurrences[2] == date(2027, 12, 31)

    def test_yearly_every_2_years(self):
        """Yearly every 2 years."""
        pattern = {
            "type": RecurrenceType.YEARLY.value,
            "month": 6,
            "day_of_month": 1,
            "interval": 2
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 1, 1),
            date(2029, 12, 31)
        )

        # 2025, 2027, 2029
        assert len(occurrences) == 3
        assert occurrences[0] == date(2025, 6, 1)
        assert occurrences[1] == date(2027, 6, 1)
        assert occurrences[2] == date(2029, 6, 1)


class TestOccurrenceExpansionPeriodOnce:
    """Test occurrence expansion for 'period_once' recurrence type."""

    def test_period_once_single_month(self):
        """Period once in January."""
        pattern = {
            "type": RecurrenceType.PERIOD_ONCE.value,
            "months": [1]
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 1, 1),
            date(2027, 12, 31)
        )

        # Once per year in Jan: 2025, 2026, 2027
        assert len(occurrences) == 3
        assert occurrences[0] == date(2025, 1, 1)
        assert occurrences[1] == date(2026, 1, 1)
        assert occurrences[2] == date(2027, 1, 1)

    def test_period_once_summer_months(self):
        """Period once in summer (Jun, Jul, Aug, Sep)."""
        pattern = {
            "type": RecurrenceType.PERIOD_ONCE.value,
            "months": [6, 7, 8, 9]
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # Once in each month: Jun, Jul, Aug, Sep
        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 6, 1)
        assert occurrences[1] == date(2026, 7, 1)
        assert occurrences[2] == date(2026, 8, 1)
        assert occurrences[3] == date(2026, 9, 1)


class TestOccurrenceExpansionPeriodYearly:
    """Test occurrence expansion for 'period_yearly' recurrence type."""

    def test_period_yearly_quarterly(self):
        """Period yearly quarterly (Mar, Jun, Sep, Dec)."""
        pattern = {
            "type": RecurrenceType.PERIOD_YEARLY.value,
            "months": [3, 6, 9, 12],
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 3, 1)
        assert occurrences[1] == date(2026, 6, 1)
        assert occurrences[2] == date(2026, 9, 1)
        assert occurrences[3] == date(2026, 12, 1)

    def test_period_yearly_every_2_years(self):
        """Period yearly every 2 years."""
        pattern = {
            "type": RecurrenceType.PERIOD_YEARLY.value,
            "months": [1, 6],
            "interval": 2
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 1, 1),
            date(2029, 12, 31)
        )

        # 2025: Jan, Jun; 2027: Jan, Jun; 2029: Jan, Jun
        assert len(occurrences) == 6
        assert occurrences[0] == date(2025, 1, 1)
        assert occurrences[1] == date(2025, 6, 1)
        assert occurrences[2] == date(2027, 1, 1)
        assert occurrences[3] == date(2027, 6, 1)
        assert occurrences[4] == date(2029, 1, 1)
        assert occurrences[5] == date(2029, 6, 1)


class TestOccurrenceExpansionEdgeCases:
    """Test edge cases for occurrence expansion."""

    def test_no_recurrence_pattern(self):
        """None pattern returns empty list."""
        occurrences = _expand_recurrence_pattern(
            {},
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        assert len(occurrences) == 0

    def test_empty_recurrence_pattern(self):
        """Empty recurrence pattern returns empty list."""
        occurrences = _expand_recurrence_pattern(
            {},
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        assert len(occurrences) == 0

    def test_invalid_recurrence_type(self):
        """Invalid recurrence type returns empty list."""
        occurrences = _expand_recurrence_pattern(
            {"type": "invalid_type"},
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        assert len(occurrences) == 0

    def test_leap_year_february_29(self):
        """Handles leap year February 29 correctly."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 29,
            "interval": 1
        }

        # 2024 is a leap year, 2025 is not
        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2024, 1, 1),
            date(2025, 3, 31)
        )

        # Should handle Feb correctly (29 in 2024, 28 in 2025)
        feb_2024 = date(2024, 2, 29)
        feb_2025 = date(2025, 2, 28)

        assert feb_2024 in occurrences
        assert feb_2025 in occurrences

    def test_occurrences_are_sorted(self):
        """Occurrences are returned in chronological order."""
        pattern = {
            "type": RecurrenceType.WEEKLY.value,
            "weekday": 0,  # Monday
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Check that occurrences are sorted
        for i in range(len(occurrences) - 1):
            assert occurrences[i] < occurrences[i + 1]

    def test_no_duplicate_occurrences(self):
        """No duplicate occurrences even with postpone."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 1,
            "postpone_weekend": True
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 14),  # Saturday
            date(2026, 2, 16)   # Monday
        )

        # Sat -> Mon, Sun -> Mon, Mon -> Mon
        # Should only have one Monday occurrence
        assert len(occurrences) == len(set(occurrences))
