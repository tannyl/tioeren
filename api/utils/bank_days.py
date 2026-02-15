"""Bank day utilities for adjusting dates to working days.

Supports country-specific holiday calendars for determining bank days
(weekdays that are not public holidays).
"""

from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import date, timedelta
from functools import lru_cache


def _compute_easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm.

    Args:
        year: Year to compute Easter for

    Returns:
        Date of Easter Sunday
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


class HolidayCalendar(ABC):
    """Base class for country-specific holiday calendars."""

    @abstractmethod
    def get_holidays(self, year: int) -> set[date]:
        """Return all public holidays for the given year.

        Args:
            year: Year to get holidays for

        Returns:
            Set of dates that are public holidays
        """
        ...


class DanishHolidayCalendar(HolidayCalendar):
    """Danish public holidays, algorithmically computed."""

    def get_holidays(self, year: int) -> set[date]:
        """Return all Danish public holidays for the given year.

        Danish public holidays:
        - Fixed dates: New Year's Day, Constitution Day, Christmas Day, Boxing Day
        - Easter-based: Maundy Thursday, Good Friday, Easter Sunday, Easter Monday,
          Ascension Day, Whit Sunday, Whit Monday

        Args:
            year: Year to get holidays for

        Returns:
            Set of dates that are Danish public holidays
        """
        holidays = set()

        # Fixed holidays
        holidays.add(date(year, 1, 1))   # Nytårsdag (New Year's Day)
        holidays.add(date(year, 6, 5))   # Grundlovsdag (Constitution Day)
        holidays.add(date(year, 12, 25)) # Juledag (Christmas Day)
        holidays.add(date(year, 12, 26)) # 2. Juledag (Boxing Day)

        # Easter-based holidays (use computus algorithm)
        easter = _compute_easter(year)
        holidays.add(easter - timedelta(days=3))  # Skærtorsdag (Maundy Thursday)
        holidays.add(easter - timedelta(days=2))  # Langfredag (Good Friday)
        holidays.add(easter)                        # Påskedag (Easter Sunday)
        holidays.add(easter + timedelta(days=1))  # 2. Påskedag (Easter Monday)
        holidays.add(easter + timedelta(days=39)) # Kristi Himmelfartsdag (Ascension Day)
        holidays.add(easter + timedelta(days=49)) # Pinsedag (Whit Sunday)
        holidays.add(easter + timedelta(days=50)) # 2. Pinsedag (Whit Monday)

        return holidays


# Registry of holiday calendars by country code
CALENDARS: dict[str, type[HolidayCalendar]] = {
    "DK": DanishHolidayCalendar,
}


@lru_cache(maxsize=128)
def _get_holidays(year: int, country: str = "DK") -> frozenset[date]:
    """Get holidays for a year+country (cached).

    Args:
        year: Year to get holidays for
        country: ISO country code (default: "DK")

    Returns:
        Frozenset of holiday dates (immutable for caching)

    Raises:
        KeyError: If country code is not supported
    """
    if country not in CALENDARS:
        raise KeyError(f"Unsupported country code: {country}")

    calendar_class = CALENDARS[country]
    calendar = calendar_class()
    return frozenset(calendar.get_holidays(year))


def is_bank_day(d: date, country: str = "DK") -> bool:
    """Return True if d is a bank day (not weekend, not holiday).

    A bank day is a weekday (Monday-Friday) that is not a public holiday.

    Args:
        d: Date to check
        country: ISO country code (default: "DK")

    Returns:
        True if the date is a bank day, False otherwise

    Raises:
        KeyError: If country code is not supported
    """
    return d.weekday() < 5 and d not in _get_holidays(d.year, country)


def next_bank_day(d: date, country: str = "DK") -> date:
    """Return d if it's a bank day, otherwise the next bank day.

    Args:
        d: Date to adjust
        country: ISO country code (default: "DK")

    Returns:
        The input date if it's a bank day, otherwise the next bank day

    Raises:
        KeyError: If country code is not supported
    """
    while not is_bank_day(d, country):
        d += timedelta(days=1)
    return d


def previous_bank_day(d: date, country: str = "DK") -> date:
    """Return d if it's a bank day, otherwise the previous bank day.

    Args:
        d: Date to adjust
        country: ISO country code (default: "DK")

    Returns:
        The input date if it's a bank day, otherwise the previous bank day

    Raises:
        KeyError: If country code is not supported
    """
    while not is_bank_day(d, country):
        d -= timedelta(days=1)
    return d


def adjust_to_bank_day(d: date, direction: str, country: str = "DK") -> date:
    """Adjust date to bank day with month boundary clamping.

    If the adjustment would cross a month boundary, uses the opposite
    direction to stay within the same month.

    Args:
        d: Date to adjust
        direction: "next" or "previous" (or "none" for no adjustment)
        country: ISO country code (default: "DK")

    Returns:
        The adjusted date (or original if direction is "none")

    Raises:
        KeyError: If country code is not supported
    """
    if direction == "next":
        adjusted = next_bank_day(d, country)
        if adjusted.month != d.month:
            # Would cross month boundary, use previous instead
            adjusted = previous_bank_day(d, country)
        return adjusted
    elif direction == "previous":
        adjusted = previous_bank_day(d, country)
        if adjusted.month != d.month:
            # Would cross month boundary, use next instead
            adjusted = next_bank_day(d, country)
        return adjusted
    return d  # "none" or unknown


def nth_bank_day_in_month(year: int, month: int, n: int, from_end: bool = False, country: str = "DK") -> date | None:
    """Get the Nth bank day in a month.

    Args:
        year: Year
        month: Month (1-12)
        n: Which bank day to find (1 = first bank day, 2 = second, etc.)
        from_end: If True, count from end of month (n=1 means last bank day)
        country: ISO country code (default: "DK")

    Returns:
        Date of the Nth bank day, or None if the month doesn't have N bank days

    Raises:
        KeyError: If country code is not supported
    """
    last_day = monthrange(year, month)[1]

    if from_end:
        # Count backwards from end of month
        bank_day_count = 0
        for day_num in range(last_day, 0, -1):
            d = date(year, month, day_num)
            if is_bank_day(d, country):
                bank_day_count += 1
                if bank_day_count == n:
                    return d
    else:
        # Count forwards from start of month
        bank_day_count = 0
        for day_num in range(1, last_day + 1):
            d = date(year, month, day_num)
            if is_bank_day(d, country):
                bank_day_count += 1
                if bank_day_count == n:
                    return d

    # Not enough bank days in the month
    return None
