"""Tests for bank_days utility module."""

import pytest
from datetime import date

from api.utils.bank_days import (
    _compute_easter,
    is_bank_day,
    next_bank_day,
    previous_bank_day,
    adjust_to_bank_day,
    nth_bank_day_in_month,
    DanishHolidayCalendar,
)


class TestEasterComputation:
    """Test Easter date computation using Anonymous Gregorian algorithm."""

    def test_easter_2024(self):
        """Easter 2024 is March 31."""
        assert _compute_easter(2024) == date(2024, 3, 31)

    def test_easter_2025(self):
        """Easter 2025 is April 20."""
        assert _compute_easter(2025) == date(2025, 4, 20)

    def test_easter_2026(self):
        """Easter 2026 is April 5."""
        assert _compute_easter(2026) == date(2026, 4, 5)

    def test_easter_2027(self):
        """Easter 2027 is March 28."""
        assert _compute_easter(2027) == date(2027, 3, 28)


class TestDanishHolidays:
    """Test Danish holiday calendar."""

    def test_danish_holidays_2026(self):
        """Test all 11 Danish public holidays in 2026."""
        calendar = DanishHolidayCalendar()
        holidays = calendar.get_holidays(2026)

        # Easter 2026 is April 5
        expected = {
            date(2026, 1, 1),   # Nytårsdag
            date(2026, 4, 2),   # Skærtorsdag (Easter - 3 days)
            date(2026, 4, 3),   # Langfredag (Easter - 2 days)
            date(2026, 4, 5),   # Påskedag (Easter)
            date(2026, 4, 6),   # 2. Påskedag (Easter + 1 day)
            date(2026, 5, 14),  # Kristi Himmelfartsdag (Easter + 39 days)
            date(2026, 5, 24),  # Pinsedag (Easter + 49 days)
            date(2026, 5, 25),  # 2. Pinsedag (Easter + 50 days)
            date(2026, 6, 5),   # Grundlovsdag
            date(2026, 12, 25), # Juledag
            date(2026, 12, 26), # 2. Juledag
        }

        assert holidays == expected
        assert len(holidays) == 11

    def test_danish_holidays_different_years(self):
        """Holidays change based on Easter date across years."""
        calendar = DanishHolidayCalendar()

        holidays_2024 = calendar.get_holidays(2024)
        holidays_2025 = calendar.get_holidays(2025)

        # Fixed holidays should be the same
        assert date(2024, 1, 1) in holidays_2024
        assert date(2025, 1, 1) in holidays_2025

        # Easter-based holidays should differ
        # Easter 2024: March 31, Easter 2025: April 20
        assert date(2024, 3, 29) in holidays_2024  # Langfredag 2024
        assert date(2025, 4, 18) in holidays_2025  # Langfredag 2025


class TestIsBankDay:
    """Test is_bank_day function."""

    def test_weekday_non_holiday(self):
        """Regular weekday that's not a holiday is a bank day."""
        # Feb 10, 2026 is a Tuesday, not a holiday
        assert is_bank_day(date(2026, 2, 10)) is True

    def test_saturday_not_bank_day(self):
        """Saturday is not a bank day."""
        # Feb 14, 2026 is a Saturday
        assert is_bank_day(date(2026, 2, 14)) is False

    def test_sunday_not_bank_day(self):
        """Sunday is not a bank day."""
        # Feb 15, 2026 is a Sunday
        assert is_bank_day(date(2026, 2, 15)) is False

    def test_holiday_not_bank_day(self):
        """Holiday is not a bank day, even on weekday."""
        # June 5, 2026 is Grundlovsdag (Friday)
        assert is_bank_day(date(2026, 6, 5)) is False

    def test_christmas_not_bank_day(self):
        """Christmas Day is not a bank day."""
        assert is_bank_day(date(2026, 12, 25)) is False

    def test_new_year_not_bank_day(self):
        """New Year's Day is not a bank day."""
        assert is_bank_day(date(2026, 1, 1)) is False


class TestNextBankDay:
    """Test next_bank_day function."""

    def test_already_bank_day(self):
        """If already a bank day, return same date."""
        # Feb 10, 2026 is a Tuesday, not a holiday
        d = date(2026, 2, 10)
        assert next_bank_day(d) == d

    def test_saturday_to_monday(self):
        """Saturday advances to Monday."""
        # Feb 14, 2026 is Saturday -> Feb 16, 2026 is Monday
        assert next_bank_day(date(2026, 2, 14)) == date(2026, 2, 16)

    def test_sunday_to_monday(self):
        """Sunday advances to Monday."""
        # Feb 15, 2026 is Sunday -> Feb 16, 2026 is Monday
        assert next_bank_day(date(2026, 2, 15)) == date(2026, 2, 16)

    def test_holiday_to_next_bank_day(self):
        """Holiday advances to next bank day."""
        # June 5, 2026 is Grundlovsdag (Friday) -> June 8 (Monday)
        assert next_bank_day(date(2026, 6, 5)) == date(2026, 6, 8)

    def test_holiday_chain_easter(self):
        """Multiple holidays in a row (Easter weekend)."""
        # April 3, 2026 is Langfredag (Good Friday)
        # -> April 5 is Påskedag (Easter Sunday)
        # -> April 6 is 2. Påskedag (Easter Monday)
        # -> Next bank day is April 7 (Tuesday)
        assert next_bank_day(date(2026, 4, 3)) == date(2026, 4, 7)


class TestPreviousBankDay:
    """Test previous_bank_day function."""

    def test_already_bank_day(self):
        """If already a bank day, return same date."""
        # Feb 10, 2026 is a Tuesday, not a holiday
        d = date(2026, 2, 10)
        assert previous_bank_day(d) == d

    def test_saturday_to_friday(self):
        """Saturday goes back to Friday."""
        # Feb 14, 2026 is Saturday -> Feb 13, 2026 is Friday
        assert previous_bank_day(date(2026, 2, 14)) == date(2026, 2, 13)

    def test_sunday_to_friday(self):
        """Sunday goes back to Friday."""
        # Feb 15, 2026 is Sunday -> Feb 13, 2026 is Friday
        assert previous_bank_day(date(2026, 2, 15)) == date(2026, 2, 13)

    def test_holiday_to_previous_bank_day(self):
        """Holiday goes back to previous bank day."""
        # June 5, 2026 is Grundlovsdag (Friday) -> June 4 (Thursday)
        assert previous_bank_day(date(2026, 6, 5)) == date(2026, 6, 4)

    def test_holiday_chain_easter(self):
        """Multiple holidays in a row (Easter weekend)."""
        # April 6, 2026 is 2. Påskedag (Easter Monday)
        # -> April 5 is Påskedag (Easter Sunday)
        # -> April 3 is Langfredag (Good Friday)
        # -> Previous bank day is April 2 (Thursday, Skærtorsdag - also holiday!)
        # -> Previous bank day is April 1 (Wednesday)
        assert previous_bank_day(date(2026, 4, 6)) == date(2026, 4, 1)


class TestAdjustToBankDay:
    """Test adjust_to_bank_day with month boundary clamping."""

    def test_none_adjustment(self):
        """Direction 'none' returns original date."""
        # Feb 14, 2026 is Saturday
        d = date(2026, 2, 14)
        assert adjust_to_bank_day(d, "none") == d

    def test_already_bank_day_next(self):
        """Already a bank day, return same with 'next'."""
        d = date(2026, 2, 10)  # Tuesday
        assert adjust_to_bank_day(d, "next") == d

    def test_already_bank_day_previous(self):
        """Already a bank day, return same with 'previous'."""
        d = date(2026, 2, 10)  # Tuesday
        assert adjust_to_bank_day(d, "previous") == d

    def test_saturday_next_same_month(self):
        """Saturday with 'next' stays in same month."""
        # Feb 14, 2026 is Saturday -> Feb 16 (Monday), same month
        assert adjust_to_bank_day(date(2026, 2, 14), "next") == date(2026, 2, 16)

    def test_saturday_previous_same_month(self):
        """Saturday with 'previous' stays in same month."""
        # Feb 14, 2026 is Saturday -> Feb 13 (Friday), same month
        assert adjust_to_bank_day(date(2026, 2, 14), "previous") == date(2026, 2, 13)

    def test_month_boundary_next_clamps_to_previous(self):
        """If 'next' would cross month boundary, use 'previous' instead."""
        # Jan 31, 2026 is Saturday
        # Next bank day would be Feb 2 (Monday) - crosses boundary
        # So it should use previous instead -> Jan 30 (Friday)
        assert adjust_to_bank_day(date(2026, 1, 31), "next") == date(2026, 1, 30)

    def test_month_boundary_previous_clamps_to_next(self):
        """If 'previous' would cross month boundary, use 'next' instead."""
        # March 1, 2026 is Sunday
        # Previous bank day would be Feb 27 (Friday) - crosses boundary
        # So it should use next instead -> March 2 (Monday)
        assert adjust_to_bank_day(date(2026, 3, 1), "previous") == date(2026, 3, 2)

    def test_weekday_within_month(self):
        """Normal weekday adjustment stays within month."""
        # Dec 31, 2025 is Wednesday (a bank day)
        d = date(2025, 12, 31)
        assert adjust_to_bank_day(d, "next") == d
        assert adjust_to_bank_day(d, "previous") == d


class TestUnsupportedCountry:
    """Test error handling for unsupported country codes."""

    def test_unknown_country_raises_error(self):
        """Unknown country code should raise KeyError."""
        with pytest.raises(KeyError, match="Unsupported country code: XX"):
            is_bank_day(date(2026, 2, 10), country="XX")

    def test_unknown_country_next_bank_day(self):
        """Unknown country code in next_bank_day should raise KeyError."""
        with pytest.raises(KeyError, match="Unsupported country code: XX"):
            next_bank_day(date(2026, 2, 10), country="XX")

    def test_unknown_country_previous_bank_day(self):
        """Unknown country code in previous_bank_day should raise KeyError."""
        with pytest.raises(KeyError, match="Unsupported country code: XX"):
            previous_bank_day(date(2026, 2, 10), country="XX")

    def test_unknown_country_adjust_to_bank_day(self):
        """Unknown country code in adjust_to_bank_day should raise KeyError."""
        with pytest.raises(KeyError, match="Unsupported country code: XX"):
            adjust_to_bank_day(date(2026, 2, 10), "next", country="XX")


class TestNthBankDayInMonth:
    """Test nth_bank_day_in_month function."""

    def test_first_bank_day_from_start(self):
        """First bank day of Jan 2026 is Jan 2 (Jan 1 is Nytårsdag)."""
        # Jan 1, 2026 is Thursday (Nytårsdag - holiday)
        # Jan 2, 2026 is Friday (1st bank day)
        assert nth_bank_day_in_month(2026, 1, 1, from_end=False) == date(2026, 1, 2)

    def test_third_bank_day_from_start(self):
        """Third bank day of Jan 2026 is Jan 6."""
        # Jan 1 Thu (holiday), Jan 2 Fri (1st), Jan 3 Sat, Jan 4 Sun, Jan 5 Mon (2nd), Jan 6 Tue (3rd)
        assert nth_bank_day_in_month(2026, 1, 3, from_end=False) == date(2026, 1, 6)

    def test_first_bank_day_from_end(self):
        """Last bank day of Dec 2026 is Dec 31."""
        # Dec 25 Fri (Juledag - holiday), Dec 26 Sat (2. Juledag - holiday)
        # Dec 27 Sun, Dec 28 Mon, Dec 29 Tue, Dec 30 Wed, Dec 31 Thu (last bank day)
        assert nth_bank_day_in_month(2026, 12, 1, from_end=True) == date(2026, 12, 31)

    def test_second_bank_day_from_end(self):
        """Second bank day from end of Dec 2026 is Dec 30."""
        # Dec 31 Thu (1st from end), Dec 30 Wed (2nd from end)
        assert nth_bank_day_in_month(2026, 12, 2, from_end=True) == date(2026, 12, 30)

    def test_too_many_returns_none(self):
        """Requesting 25th bank day should return None (no month has 25 bank days)."""
        assert nth_bank_day_in_month(2026, 2, 25, from_end=False) is None

    def test_tenth_bank_day(self):
        """Tenth bank day of Feb 2026."""
        # Feb 2026 starts on Sunday (Feb 1)
        # Feb 2 Mon (1st), Feb 3 Tue (2nd), Feb 4 Wed (3rd), Feb 5 Thu (4th), Feb 6 Fri (5th)
        # Feb 7 Sat, Feb 8 Sun
        # Feb 9 Mon (6th), Feb 10 Tue (7th), Feb 11 Wed (8th), Feb 12 Thu (9th), Feb 13 Fri (10th)
        assert nth_bank_day_in_month(2026, 2, 10, from_end=False) == date(2026, 2, 13)

    def test_month_with_holidays(self):
        """First bank day of April 2026 (month with Easter holidays)."""
        # April 2026: Easter is April 5
        # April 1 Wed, April 2 Thu (Skærtorsdag - holiday), April 3 Fri (Langfredag - holiday)
        # April 4 Sat, April 5 Sun (Påskedag - holiday), April 6 Mon (2. Påskedag - holiday)
        # April 7 Tue (1st bank day)
        assert nth_bank_day_in_month(2026, 4, 1, from_end=False) == date(2026, 4, 1)

    def test_second_bank_day_april_2026(self):
        """Second bank day of April 2026."""
        # April 1 Wed (1st), April 2-6 holidays/weekend, April 7 Tue (2nd)
        assert nth_bank_day_in_month(2026, 4, 2, from_end=False) == date(2026, 4, 7)
