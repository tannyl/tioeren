"""Tests for non-bank-days API endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestNonBankDaysEndpoint:
    """Tests for GET /api/bank-days/non-bank-days"""

    def test_valid_date_range_returns_non_bank_days(
        self,
        authenticated_client: TestClient,
    ):
        """Test that valid date range returns weekends and holidays."""
        # Test range: 2026-02-01 to 2026-02-28 (February 2026)
        # Expected non-bank-days:
        # - Weekends: Feb 1 (Sun), 7, 8, 14, 15, 21, 22, 28
        # - No Danish holidays in Feb 2026
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        dates = data["dates"]

        # Should contain all weekend days in February 2026
        expected_weekends = [
            "2026-02-01",  # Sunday
            "2026-02-07",  # Saturday
            "2026-02-08",  # Sunday
            "2026-02-14",  # Saturday
            "2026-02-15",  # Sunday
            "2026-02-21",  # Saturday
            "2026-02-22",  # Sunday
            "2026-02-28",  # Saturday
        ]

        for weekend in expected_weekends:
            assert weekend in dates, f"Expected weekend {weekend} to be in non-bank-days"

    def test_includes_danish_holidays(
        self,
        authenticated_client: TestClient,
    ):
        """Test that Danish public holidays are included as non-bank-days."""
        # Test range including New Year's Day 2026
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2025-12-28",
                "to_date": "2026-01-04",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        dates = data["dates"]

        # New Year's Day 2026 (Jan 1, Thursday) should be included
        assert "2026-01-01" in dates

        # Weekend days should also be included
        assert "2025-12-28" in dates  # Sunday
        assert "2026-01-03" in dates  # Saturday
        assert "2026-01-04" in dates  # Sunday

    def test_bank_days_not_included(
        self,
        authenticated_client: TestClient,
    ):
        """Test that regular bank days (weekdays, no holidays) are NOT included."""
        # Test a week with no holidays
        # 2026-02-02 (Mon) to 2026-02-06 (Fri) - all bank days
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-02",
                "to_date": "2026-02-06",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        dates = data["dates"]

        # Should be empty - all days are bank days
        assert len(dates) == 0

    def test_max_range_exceeded_returns_400(
        self,
        authenticated_client: TestClient,
    ):
        """Test that date range exceeding 366 days returns 400."""
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-01-01",
                "to_date": "2027-01-02",  # 367 days
                "country": "DK",
            },
        )

        assert response.status_code == 400
        assert "exceed 366 days" in response.json()["detail"]

    def test_max_range_366_days_accepted(
        self,
        authenticated_client: TestClient,
    ):
        """Test that exactly 366 days is accepted."""
        # Leap year: 2024-01-01 to 2024-12-31 = 366 days
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "dates" in data

    def test_invalid_date_format_returns_422(
        self,
        authenticated_client: TestClient,
    ):
        """Test that invalid date format returns 422."""
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-01",
                "to_date": "invalid-date",
                "country": "DK",
            },
        )

        assert response.status_code == 422
        assert "Invalid date format" in response.json()["detail"]

    def test_from_date_after_to_date_returns_400(
        self,
        authenticated_client: TestClient,
    ):
        """Test that from_date after to_date returns 400."""
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-15",
                "to_date": "2026-02-01",
                "country": "DK",
            },
        )

        assert response.status_code == 400
        assert "from_date must be before or equal to to_date" in response.json()["detail"]

    def test_unsupported_country_code_returns_400(
        self,
        authenticated_client: TestClient,
    ):
        """Test that unsupported country code returns 400."""
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28",
                "country": "US",  # Not supported
            },
        )

        assert response.status_code == 400
        assert "Unsupported country code" in response.json()["detail"]

    def test_unauthenticated_request_returns_401(
        self,
        client: TestClient,
    ):
        """Test that unauthenticated request returns 401."""
        response = client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28",
                "country": "DK",
            },
        )

        assert response.status_code == 401

    def test_default_country_is_dk(
        self,
        authenticated_client: TestClient,
    ):
        """Test that country parameter defaults to DK."""
        # Omit country parameter - should default to DK
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-01-01",
                "to_date": "2026-01-01",
            },
        )

        assert response.status_code == 200
        data = response.json()
        dates = data["dates"]

        # Jan 1, 2026 is New Year's Day (Thursday) - should be a holiday in DK
        assert "2026-01-01" in dates

    def test_single_day_range(
        self,
        authenticated_client: TestClient,
    ):
        """Test querying a single day."""
        # Saturday - should be a non-bank-day
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-07",
                "to_date": "2026-02-07",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        dates = data["dates"]

        assert len(dates) == 1
        assert dates[0] == "2026-02-07"

    def test_dates_are_sorted(
        self,
        authenticated_client: TestClient,
    ):
        """Test that returned dates are sorted in ascending order."""
        response = authenticated_client.get(
            "/api/bank-days/non-bank-days",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-15",
                "country": "DK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        dates = data["dates"]

        # Verify dates are sorted
        assert dates == sorted(dates)
