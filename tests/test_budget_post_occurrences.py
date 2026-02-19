"""Tests for recurrence pattern expansion to concrete occurrence dates."""

import pytest
from datetime import date
from uuid import uuid4
from unittest.mock import Mock

from api.models.budget_post import BudgetPostType
from api.schemas.budget_post import RecurrenceType, RelativePosition, BankDayAdjustment
from api.services.budget_post_service import (
    _expand_recurrence_pattern,
    expand_amount_patterns_to_occurrences,
    expand_patterns_from_data,
)


class TestOccurrenceExpansionOnce:
    """Test occurrence expansion for 'once' recurrence type."""

    def _create_budget_post_with_pattern(self, start_date: date, amount: int, recurrence_pattern: dict):
        """Helper to create a mock BudgetPost with an AmountPattern."""
        mock_pattern = Mock()
        mock_pattern.start_date = start_date
        mock_pattern.end_date = None
        mock_pattern.amount = amount
        mock_pattern.recurrence_pattern = recurrence_pattern

        mock_budget_post = Mock()
        mock_budget_post.amount_patterns = [mock_pattern]

        return mock_budget_post

    def test_once_within_range(self):
        """Single occurrence within range."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 2, 15),
            amount=10000,
            recurrence_pattern={"type": RecurrenceType.ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 15), 10000)

    def test_once_before_range(self):
        """Single occurrence before range."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 1, 15),
            amount=10000,
            recurrence_pattern={"type": RecurrenceType.ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_once_after_range(self):
        """Single occurrence after range."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 3, 15),
            amount=10000,
            recurrence_pattern={"type": RecurrenceType.ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_once_on_saturday_with_bank_day_adjustment(self):
        """Occurrence on Saturday adjusted to Monday (next bank day)."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 2, 14),  # Saturday
            amount=10000,
            recurrence_pattern={
                "type": RecurrenceType.ONCE.value,
                "bank_day_adjustment": "next"
            }
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 16), 10000)  # Monday

    def test_once_on_sunday_with_bank_day_adjustment(self):
        """Occurrence on Sunday adjusted to Monday (next bank day)."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 2, 15),  # Sunday
            amount=10000,
            recurrence_pattern={
                "type": RecurrenceType.ONCE.value,
                "bank_day_adjustment": "next"
            }
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 16), 10000)  # Monday

    def test_once_on_saturday_with_previous_bank_day(self):
        """Occurrence on Saturday adjusted to Friday (previous bank day)."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 2, 14),  # Saturday
            amount=10000,
            recurrence_pattern={
                "type": RecurrenceType.ONCE.value,
                "bank_day_adjustment": "previous"
            }
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 13), 10000)  # Friday


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

    def test_monthly_with_bank_day_adjustment_on_sunday(self):
        """Monthly on 1st with next bank day adjustment (Feb 1, 2026 is Sunday)."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 1,
            "interval": 1,
            "bank_day_adjustment": "next"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Feb 1, 2026 is a Sunday, should be adjusted to Monday Feb 2
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 2)

    def test_monthly_on_holiday_adjusted_to_next_bank_day(self):
        """Monthly on day that's a holiday gets adjusted to next bank day."""
        # June 5, 2026 is Grundlovsdag (Friday), a Danish holiday
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 5,
            "interval": 1,
            "bank_day_adjustment": "next"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 6, 1),
            date(2026, 6, 30)
        )

        # June 5 is Grundlovsdag -> next bank day is June 8 (Monday)
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 6, 8)

    def test_monthly_with_bank_day_adjustment_crossing_month_allowed(self):
        """Monthly on 31st with next bank day adjustment and keep_in_month=False allows crossing."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 31,
            "interval": 1,
            "bank_day_adjustment": "next",
            "bank_day_keep_in_month": False
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 2, 28)
        )

        # Jan 31, 2026 is a Saturday
        # With keep_in_month=False, next bank day is Feb 2 (Monday) - crosses boundary
        # Feb 28, 2026 is a Saturday
        # With keep_in_month=False, next bank day is Mar 2 (Monday) - crosses boundary (outside range)
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 2)

    def test_monthly_with_bank_day_adjustment_crossing_month_not_allowed(self):
        """Monthly on 31st with next bank day adjustment and keep_in_month=True stays within month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_FIXED.value,
            "day_of_month": 31,
            "interval": 1,
            "bank_day_adjustment": "next",
            "bank_day_keep_in_month": True  # Explicit True
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 2, 28)
        )

        # Jan 31, 2026 is a Saturday
        # With keep_in_month=True, next would be Feb 2 but that crosses month, so use previous -> Jan 30
        # Feb 28, 2026 is a Saturday
        # With keep_in_month=True, next would be Mar 2 but that crosses month, so use previous -> Feb 27
        assert len(occurrences) == 2
        assert occurrences[0] == date(2026, 1, 30)
        assert occurrences[1] == date(2026, 2, 27)


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

    def test_monthly_second_tuesday(self):
        """Second Tuesday of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_RELATIVE.value,
            "weekday": 1,  # Tuesday
            "relative_position": RelativePosition.SECOND.value,
            "interval": 1
        }
        occurrences = _expand_recurrence_pattern(
            pattern, date(2026, 1, 1), date(2026, 3, 31)
        )
        # 2nd Tuesdays: Jan 13, Feb 10, Mar 10
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 13)
        assert occurrences[1] == date(2026, 2, 10)
        assert occurrences[2] == date(2026, 3, 10)

    def test_monthly_third_wednesday(self):
        """Third Wednesday of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_RELATIVE.value,
            "weekday": 2,  # Wednesday
            "relative_position": RelativePosition.THIRD.value,
            "interval": 1
        }
        occurrences = _expand_recurrence_pattern(
            pattern, date(2026, 1, 1), date(2026, 3, 31)
        )
        # 3rd Wednesdays: Jan 21, Feb 18, Mar 18
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 21)
        assert occurrences[1] == date(2026, 2, 18)
        assert occurrences[2] == date(2026, 3, 18)

    def test_monthly_fourth_friday(self):
        """Fourth Friday of every month."""
        pattern = {
            "type": RecurrenceType.MONTHLY_RELATIVE.value,
            "weekday": 4,  # Friday
            "relative_position": RelativePosition.FOURTH.value,
            "interval": 1
        }
        occurrences = _expand_recurrence_pattern(
            pattern, date(2026, 1, 1), date(2026, 3, 31)
        )
        # 4th Fridays: Jan 23, Feb 27, Mar 27
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 23)
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

    def test_yearly_second_monday_of_june(self):
        """Yearly on second Monday of June."""
        pattern = {
            "type": RecurrenceType.YEARLY.value,
            "month": 6,
            "weekday": 0,  # Monday
            "relative_position": RelativePosition.SECOND.value,
            "interval": 1
        }
        occurrences = _expand_recurrence_pattern(
            pattern, date(2025, 1, 1), date(2027, 12, 31)
        )
        # 2nd Monday of June: 2025-06-09, 2026-06-08, 2027-06-14
        assert len(occurrences) == 3
        assert occurrences[0] == date(2025, 6, 9)
        assert occurrences[1] == date(2026, 6, 8)
        assert occurrences[2] == date(2027, 6, 14)

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

    def _create_budget_post_with_pattern(self, start_date: date, amount: int, recurrence_pattern: dict):
        """Helper to create a mock BudgetPost with an AmountPattern."""
        mock_pattern = Mock()
        mock_pattern.start_date = start_date
        mock_pattern.end_date = None
        mock_pattern.amount = amount
        mock_pattern.recurrence_pattern = recurrence_pattern

        mock_budget_post = Mock()
        mock_budget_post.amount_patterns = [mock_pattern]

        return mock_budget_post

    def test_period_once_uses_start_date_year_month(self):
        """Period once uses start_date year+month for single occurrence."""
        # Start date is 2026-06-15 → occurrence in 2026-06
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 6, 15),
            amount=50000,
            recurrence_pattern={"type": RecurrenceType.PERIOD_ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # Should only have one occurrence in June 2026
        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 6, 1), 50000)

    def test_period_once_wide_range_single_occurrence(self):
        """Period once querying wide range only produces occurrence in start_date month."""
        # Start date is 2026-03-20 → occurrence only in 2026-03
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2026, 3, 20),
            amount=30000,
            recurrence_pattern={"type": RecurrenceType.PERIOD_ONCE.value}
        )

        # Query a wide range
        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2025, 1, 1),
            date(2030, 12, 31)
        )

        # Should only have occurrence in March 2026, not in other years
        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 3, 1), 30000)

    def test_period_once_before_range(self):
        """Period once with start_date before query range produces no occurrences."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2025, 12, 10),
            amount=20000,
            recurrence_pattern={"type": RecurrenceType.PERIOD_ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # December 2025 is before range
        assert len(occurrences) == 0

    def test_period_once_after_range(self):
        """Period once with start_date after query range produces no occurrences."""
        budget_post = self._create_budget_post_with_pattern(
            start_date=date(2027, 1, 5),
            amount=20000,
            recurrence_pattern={"type": RecurrenceType.PERIOD_ONCE.value}
        )

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # January 2027 is after range
        assert len(occurrences) == 0


class TestOccurrenceExpansionPeriodMonthly:
    """Test occurrence expansion for 'period_monthly' recurrence type."""

    def test_period_monthly_every_month(self):
        """Every month (interval=1) over a year."""
        pattern = {
            "type": RecurrenceType.PERIOD_MONTHLY.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # 12 occurrences on 1st of each month
        assert len(occurrences) == 12
        assert occurrences[0] == date(2026, 1, 1)
        assert occurrences[1] == date(2026, 2, 1)
        assert occurrences[2] == date(2026, 3, 1)
        assert occurrences[11] == date(2026, 12, 1)

    def test_period_monthly_every_3_months(self):
        """Every 3 months (quarterly)."""
        pattern = {
            "type": RecurrenceType.PERIOD_MONTHLY.value,
            "interval": 3
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # 4 occurrences: Jan, Apr, Jul, Oct
        assert len(occurrences) == 4
        assert occurrences[0] == date(2026, 1, 1)
        assert occurrences[1] == date(2026, 4, 1)
        assert occurrences[2] == date(2026, 7, 1)
        assert occurrences[3] == date(2026, 10, 1)

    def test_period_monthly_cross_year_boundary(self):
        """Period monthly crosses year boundary correctly."""
        pattern = {
            "type": RecurrenceType.PERIOD_MONTHLY.value,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2025, 11, 1),
            date(2026, 2, 28)
        )

        # Nov 2025, Dec 2025, Jan 2026, Feb 2026
        assert len(occurrences) == 4
        assert occurrences[0] == date(2025, 11, 1)
        assert occurrences[1] == date(2025, 12, 1)
        assert occurrences[2] == date(2026, 1, 1)
        assert occurrences[3] == date(2026, 2, 1)

    def test_period_monthly_with_end_date(self):
        """Period monthly respects end_date."""
        pattern = {
            "type": RecurrenceType.PERIOD_MONTHLY.value,
            "interval": 1
        }

        # Start in Jan but end in Jun
        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 6, 30)
        )

        # Should only have Jan through Jun (6 months)
        assert len(occurrences) == 6
        assert occurrences[0] == date(2026, 1, 1)
        assert occurrences[5] == date(2026, 6, 1)


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
        """No duplicate occurrences even with bank day adjustment."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 1,
            "bank_day_adjustment": "next"
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 14),  # Saturday
            date(2026, 2, 16)   # Monday
        )

        # Sat -> Mon, Sun -> Mon, Mon -> Mon
        # Should only have one Monday occurrence
        assert len(occurrences) == len(set(occurrences))

    def test_bank_day_accumulate_no_dedup(self):
        """Daily with next adjustment + no_dedup: Saturday+Sunday+Monday all land on Monday = 3 occurrences."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 1,
            "bank_day_adjustment": "next",
            "bank_day_no_dedup": True
        }
        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 14),  # Saturday
            date(2026, 2, 16)   # Monday
        )
        # Sat -> Mon, Sun -> Mon, Mon -> Mon = 3 Monday occurrences
        assert len(occurrences) == 3
        assert all(o == date(2026, 2, 16) for o in occurrences)

    def test_bank_day_no_dedup_default_false(self):
        """Default behavior (no_dedup=False) still deduplicates."""
        pattern = {
            "type": RecurrenceType.DAILY.value,
            "interval": 1,
            "bank_day_adjustment": "next"
        }
        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 14),  # Saturday
            date(2026, 2, 16)   # Monday
        )
        # Sat -> Mon, Sun -> Mon, Mon -> Mon, but dedup = only 1 occurrence
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 16)


class TestOccurrenceExpansionMonthlyBankDay:
    """Test occurrence expansion for 'monthly_bank_day' recurrence type."""

    def test_monthly_bank_day_from_start_jan_mar(self):
        """3rd bank day monthly from start for Jan-Mar 2026."""
        pattern = {
            "type": RecurrenceType.MONTHLY_BANK_DAY.value,
            "bank_day_number": 3,
            "bank_day_from_end": False,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Jan 1 is holiday (Thu), Jan 2 Fri (1st), Jan 5 Mon (2nd), Jan 6 Tue (3rd)
        # Feb 2 Mon (1st), Feb 3 Tue (2nd), Feb 4 Wed (3rd)
        # Mar 2 Mon (1st), Mar 3 Tue (2nd), Mar 4 Wed (3rd)
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 6)
        assert occurrences[1] == date(2026, 2, 4)
        assert occurrences[2] == date(2026, 3, 4)

    def test_monthly_bank_day_from_end(self):
        """2nd bank day from end monthly."""
        pattern = {
            "type": RecurrenceType.MONTHLY_BANK_DAY.value,
            "bank_day_number": 2,
            "bank_day_from_end": True,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Feb 2026: last day is 28 (Sat)
        # Feb 27 Fri (1st from end), Feb 26 Thu (2nd from end)
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 26)

    def test_monthly_bank_day_with_interval(self):
        """1st bank day every 2 months."""
        pattern = {
            "type": RecurrenceType.MONTHLY_BANK_DAY.value,
            "bank_day_number": 1,
            "bank_day_from_end": False,
            "interval": 2
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 6, 30)
        )

        # Jan, Mar, May
        # Jan 2 Fri (1st), Mar 2 Mon (1st), May 1 Fri (1st)
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 2)
        assert occurrences[1] == date(2026, 3, 2)
        assert occurrences[2] == date(2026, 5, 1)

    def test_monthly_bank_day_no_bank_day_adjustment(self):
        """Bank day types do not apply bank_day_adjustment."""
        pattern = {
            "type": RecurrenceType.MONTHLY_BANK_DAY.value,
            "bank_day_number": 1,
            "bank_day_from_end": False,
            "interval": 1,
            "bank_day_adjustment": "next"  # Should be ignored
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Feb 2 Mon is 1st bank day, should not be adjusted
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 2, 2)

    def test_monthly_bank_day_month_with_many_holidays(self):
        """Handle month with Easter holidays (April 2026)."""
        pattern = {
            "type": RecurrenceType.MONTHLY_BANK_DAY.value,
            "bank_day_number": 2,
            "bank_day_from_end": False,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 4, 1),
            date(2026, 4, 30)
        )

        # April 2026: Easter is April 5
        # April 1 Wed (1st), April 2-6 holidays/weekend, April 7 Tue (2nd)
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 4, 7)


class TestOccurrenceExpansionYearlyBankDay:
    """Test occurrence expansion for 'yearly_bank_day' recurrence type."""

    def test_yearly_bank_day_first_from_start(self):
        """1st bank day of March each year."""
        pattern = {
            "type": RecurrenceType.YEARLY_BANK_DAY.value,
            "month": 3,
            "bank_day_number": 1,
            "bank_day_from_end": False,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2028, 12, 31)
        )

        # Mar 2026: Mar 2 Mon (1st)
        # Mar 2027: Mar 1 Mon (1st)
        # Mar 2028: Mar 1 Wed (1st)
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 3, 2)
        assert occurrences[1] == date(2027, 3, 1)
        assert occurrences[2] == date(2028, 3, 1)

    def test_yearly_bank_day_from_end(self):
        """2nd bank day from end of December each year."""
        pattern = {
            "type": RecurrenceType.YEARLY_BANK_DAY.value,
            "month": 12,
            "bank_day_number": 2,
            "bank_day_from_end": True,
            "interval": 1
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2027, 12, 31)
        )

        # Dec 2026: Dec 31 Thu (1st from end), Dec 30 Wed (2nd from end)
        # Dec 2027: Dec 31 Fri (1st from end), Dec 30 Thu (2nd from end)
        assert len(occurrences) == 2
        assert occurrences[0] == date(2026, 12, 30)
        assert occurrences[1] == date(2027, 12, 30)

    def test_yearly_bank_day_with_interval(self):
        """1st bank day of January every 2 years."""
        pattern = {
            "type": RecurrenceType.YEARLY_BANK_DAY.value,
            "month": 1,
            "bank_day_number": 1,
            "bank_day_from_end": False,
            "interval": 2
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2030, 12, 31)
        )

        # 2026, 2028, 2030
        # Jan 2026: Jan 2 Fri (1st)
        # Jan 2028: Jan 3 Mon (1st, Jan 1 is Sat, Jan 2 is Sun)
        # Jan 2030: Jan 2 Wed (1st, Jan 1 is Tue holiday)
        assert len(occurrences) == 3
        assert occurrences[0] == date(2026, 1, 2)
        assert occurrences[1] == date(2028, 1, 3)
        assert occurrences[2] == date(2030, 1, 2)

    def test_yearly_bank_day_no_bank_day_adjustment(self):
        """Bank day types do not apply bank_day_adjustment."""
        pattern = {
            "type": RecurrenceType.YEARLY_BANK_DAY.value,
            "month": 3,
            "bank_day_number": 1,
            "bank_day_from_end": False,
            "interval": 1,
            "bank_day_adjustment": "previous"  # Should be ignored
        }

        occurrences = _expand_recurrence_pattern(
            pattern,
            date(2026, 1, 1),
            date(2026, 12, 31)
        )

        # Mar 2026: Mar 2 Mon is 1st bank day, should not be adjusted
        assert len(occurrences) == 1
        assert occurrences[0] == date(2026, 3, 2)


class TestExpandPatternsFromData:
    """Test expand_patterns_from_data service function for preview/charting."""

    def test_single_once_pattern(self):
        """Single once pattern returns one occurrence with pattern_id."""
        patterns = {
            "pattern-0": {
                "amount": 10000,
                "start_date": "2026-02-15",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 15), 10000, "pattern-0")

    def test_two_patterns_once_and_monthly(self):
        """Two patterns with correct pattern_id for each occurrence."""
        patterns = {
            "pattern-0": {
                "amount": 5000,
                "start_date": "2026-02-10",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            },
            "pattern-1": {
                "amount": 15000,
                "start_date": "2026-02-01",
                "end_date": "2026-03-31",
                "recurrence_pattern": {
                    "type": RecurrenceType.MONTHLY_FIXED.value,
                    "day_of_month": 15,
                    "interval": 1
                }
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 3, 31)
        )

        # Should have: once on 2/10 (pattern-0) + monthly on 2/15 and 3/15 (pattern-1)
        assert len(occurrences) == 3
        # Sorted by date
        assert occurrences[0] == (date(2026, 2, 10), 5000, "pattern-0")  # once pattern
        assert occurrences[1] == (date(2026, 2, 15), 15000, "pattern-1")  # monthly pattern
        assert occurrences[2] == (date(2026, 3, 15), 15000, "pattern-1")  # monthly pattern

    def test_period_once_pattern(self):
        """period_once pattern returns 1st-of-month date."""
        patterns = {
            "pattern-0": {
                "amount": 20000,
                "start_date": "2026-02-15",  # Any day in Feb
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.PERIOD_ONCE.value}
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 1
        assert occurrences[0] == (date(2026, 2, 1), 20000, "pattern-0")  # 1st of month

    def test_period_monthly_pattern(self):
        """period_monthly pattern returns 1st-of-month dates for each month."""
        patterns = {
            "pattern-0": {
                "amount": 30000,
                "start_date": "2026-01-01",  # Pattern starts on first of month
                "end_date": "2026-03-31",
                "recurrence_pattern": {
                    "type": RecurrenceType.PERIOD_MONTHLY.value,
                    "interval": 1
                }
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Should have 1st of Jan, Feb, Mar
        assert len(occurrences) == 3
        assert occurrences[0] == (date(2026, 1, 1), 30000, "pattern-0")
        assert occurrences[1] == (date(2026, 2, 1), 30000, "pattern-0")
        assert occurrences[2] == (date(2026, 3, 1), 30000, "pattern-0")

    def test_period_monthly_start_mid_month(self):
        """period_monthly starting mid-month skips first month occurrence."""
        patterns = {
            "pattern-0": {
                "amount": 25000,
                "start_date": "2026-01-15",  # Pattern starts mid-month
                "end_date": "2026-03-31",
                "recurrence_pattern": {
                    "type": RecurrenceType.PERIOD_MONTHLY.value,
                    "interval": 1
                }
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 1, 1),
            date(2026, 3, 31)
        )

        # Should have 1st of Feb, Mar (Jan 1 is before pattern start_date Jan 15)
        assert len(occurrences) == 2
        assert occurrences[0] == (date(2026, 2, 1), 25000, "pattern-0")
        assert occurrences[1] == (date(2026, 3, 1), 25000, "pattern-0")

    def test_mixed_period_and_date_patterns(self):
        """Mix of period-based and date-based patterns with correct pattern IDs."""
        patterns = {
            "pattern-0": {
                "amount": 10000,
                "start_date": "2026-02-01",
                "end_date": None,
                "recurrence_pattern": {
                    "type": RecurrenceType.PERIOD_MONTHLY.value,
                    "interval": 1
                }
            },
            "pattern-1": {
                "amount": 5000,
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "recurrence_pattern": {
                    "type": RecurrenceType.WEEKLY.value,
                    "weekday": 4,  # Friday
                    "interval": 1
                }
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        # Should have: period_monthly on 2/1 (pattern-0) + 4 Fridays in Feb (pattern-1)
        assert len(occurrences) == 5
        assert occurrences[0] == (date(2026, 2, 1), 10000, "pattern-0")  # period
        assert occurrences[1] == (date(2026, 2, 6), 5000, "pattern-1")   # weekly Friday
        assert occurrences[2] == (date(2026, 2, 13), 5000, "pattern-1")  # weekly Friday
        assert occurrences[3] == (date(2026, 2, 20), 5000, "pattern-1")  # weekly Friday
        assert occurrences[4] == (date(2026, 2, 27), 5000, "pattern-1")  # weekly Friday

    def test_pattern_start_after_query_range(self):
        """Pattern with start_date after query range is excluded."""
        patterns = {
            "pattern-0": {
                "amount": 10000,
                "start_date": "2026-03-15",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_empty_patterns_list(self):
        """Empty patterns dict returns empty result."""
        patterns = {}

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 0

    def test_results_sorted_by_date(self):
        """Results are sorted by date regardless of pattern order."""
        patterns = {
            "pattern-0": {
                "amount": 20000,
                "start_date": "2026-02-20",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            },
            "pattern-1": {
                "amount": 10000,
                "start_date": "2026-02-05",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            },
            "pattern-2": {
                "amount": 15000,
                "start_date": "2026-02-15",
                "end_date": None,
                "recurrence_pattern": {"type": RecurrenceType.ONCE.value}
            }
        }

        occurrences = expand_patterns_from_data(
            patterns,
            date(2026, 2, 1),
            date(2026, 2, 28)
        )

        assert len(occurrences) == 3
        # Should be sorted by date: 2/5, 2/15, 2/20
        assert occurrences[0] == (date(2026, 2, 5), 10000, "pattern-1")   # pattern-1
        assert occurrences[1] == (date(2026, 2, 15), 15000, "pattern-2")  # pattern-2
        assert occurrences[2] == (date(2026, 2, 20), 20000, "pattern-0")  # pattern-0
