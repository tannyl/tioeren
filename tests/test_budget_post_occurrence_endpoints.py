"""Tests for budget post occurrence API endpoints."""

import pytest
from datetime import date
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.models.user import User
from api.models.budget import Budget
from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection
from api.models.amount_pattern import AmountPattern
from api.schemas.budget_post import RecurrenceType, RelativePosition


@pytest.fixture
def test_budget(db: DBSession, test_user):
    """Create a test budget."""
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget




class TestGetBudgetPostOccurrences:
    """Test GET /api/budgets/{budget_id}/budget-posts/{post_id}/occurrences endpoint."""

    def test_get_occurrences_weekly(self, client, db, auth_headers, test_budget):
        """Get occurrences for weekly budget post."""
        # Create budget post with weekly recurrence (every Friday)
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=5000,  # 50 kr
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.WEEKLY.value,
                "weekday": 4,  # Friday
                "interval": 1
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        # Request occurrences for February 2026
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["budget_post_id"] == str(budget_post.id)
        assert len(data["occurrences"]) == 4  # 4 Fridays in Feb 2026

        # Check first occurrence
        assert data["occurrences"][0]["date"] == "2026-02-06"
        assert data["occurrences"][0]["amount"] == 5000

    def test_get_occurrences_monthly_fixed(self, client, db, auth_headers, test_budget):
        """Get occurrences for monthly fixed budget post."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=800000,  # 8000 kr
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.MONTHLY_FIXED.value,
                "day_of_month": 1,
                "interval": 1
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        # Request occurrences for Feb-Apr 2026
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-04-30"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["occurrences"]) == 3  # Feb, Mar, Apr
        assert data["occurrences"][0]["date"] == "2026-02-01"
        assert data["occurrences"][1]["date"] == "2026-03-01"
        assert data["occurrences"][2]["date"] == "2026-04-01"

    def test_get_occurrences_default_current_month(self, client, db, auth_headers, test_budget):
        """Get occurrences defaults to current month when dates not provided."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=1000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.DAILY.value,
                "interval": 1
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        # Request without date params (should default to current month)
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should have occurrences for current month
        assert len(data["occurrences"]) > 0

    def test_get_occurrences_ceiling_type_uses_max_amount(self, client, db, auth_headers, test_budget):
        """Ceiling type budget posts use amount from patterns."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.CEILING,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern with maximum amount
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=300000,  # 3000 kr
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.MONTHLY_FIXED.value,
                "day_of_month": 1,
                "interval": 1
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should use amount from pattern (300000)
        assert data["occurrences"][0]["amount"] == 300000

    def test_get_occurrences_with_bank_day_adjustment(self, client, db, auth_headers, test_budget):
        """Occurrences on weekends are adjusted to next bank day."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern with bank_day_adjustment
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=800000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.MONTHLY_FIXED.value,
                "day_of_month": 1,
                "interval": 1,
                "bank_day_adjustment": "next"
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        # Feb 1, 2026 is a Sunday
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should be adjusted to Monday Feb 2
        assert data["occurrences"][0]["date"] == "2026-02-02"

    def test_get_occurrences_not_found(self, client, auth_headers, test_budget):
        """Returns 404 for non-existent budget post."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{fake_id}/occurrences",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_occurrences_invalid_date_format(self, client, db, auth_headers, test_budget):
        """Returns 422 for invalid date format."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=5000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.DAILY.value
            }
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences",
            params={
                "from_date": "01-02-2026",  # Wrong format
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_get_occurrences_unauthorized(self, client, test_budget, db):
        """Returns 401 without authentication."""
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(budget_post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=5000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={"type": RecurrenceType.DAILY.value}
        )
        db.add(pattern)
        db.commit()
        db.refresh(budget_post)

        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/{budget_post.id}/occurrences"
        )

        assert response.status_code == 401


class TestGetBulkBudgetPostOccurrences:
    """Test GET /api/budgets/{budget_id}/budget-posts/occurrences endpoint."""

    def test_get_bulk_occurrences(self, client, db, auth_headers, test_budget):
        """Get occurrences for all budget posts in a budget."""
        # Create multiple budget posts
        post1 = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Udgift", "Husleje"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        post2 = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 1],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add_all([post1, post2])
        db.commit()

        # Add amount patterns
        pattern1 = AmountPattern(
            budget_post_id=post1.id,
            amount=800000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.MONTHLY_FIXED.value,
                "day_of_month": 1,
                "interval": 1
            }
        )
        pattern2 = AmountPattern(
            budget_post_id=post2.id,
            amount=5000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.WEEKLY.value,
                "weekday": 4,  # Friday
                "interval": 1
            }
        )
        db.add_all([pattern1, pattern2])
        db.commit()
        db.refresh(post1)
        db.refresh(post2)

        # Request bulk occurrences for February 2026
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2  # Two budget posts

        # Find rent and savings in response
        rent_data = next(item for item in data["data"] if item["budget_post_id"] == str(post1.id))
        savings_data = next(item for item in data["data"] if item["budget_post_id"] == str(post2.id))

        # Rent: once per month
        assert len(rent_data["occurrences"]) == 1
        assert rent_data["occurrences"][0]["date"] == "2026-02-01"
        assert rent_data["occurrences"][0]["amount"] == 800000

        # Savings: 4 Fridays in Feb
        assert len(savings_data["occurrences"]) == 4

    def test_get_bulk_occurrences_empty_budget(self, client, auth_headers, test_budget):
        """Returns empty list for budget with no budget posts."""
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/occurrences",
            params={
                "from_date": "2026-02-01",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0

    def test_get_bulk_occurrences_default_current_month(self, client, db, auth_headers, test_budget):
        """Bulk occurrences default to current month when dates not provided."""
        post = BudgetPost(
            budget_id=test_budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            type=BudgetPostType.FIXED,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account
        )
        db.add(post)
        db.commit()

        # Add amount pattern
        pattern = AmountPattern(
            budget_post_id=post.id,
            amount=1000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": RecurrenceType.DAILY.value,
                "interval": 1
            }
        )
        db.add(pattern)
        db.commit()

        # Request without date params
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/occurrences",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # Should have occurrences for current month
        assert len(data["data"][0]["occurrences"]) > 0

    def test_get_bulk_occurrences_unauthorized(self, client, test_budget):
        """Returns 401 without authentication."""
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/occurrences"
        )

        assert response.status_code == 401

    def test_get_bulk_occurrences_budget_not_found(self, client, auth_headers):
        """Returns 404 for non-existent budget."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/budgets/{fake_id}/budget-posts/occurrences",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_bulk_occurrences_invalid_date(self, client, auth_headers, test_budget):
        """Returns 422 for invalid date format."""
        response = client.get(
            f"/api/budgets/{test_budget.id}/budget-posts/occurrences",
            params={
                "from_date": "invalid-date",
                "to_date": "2026-02-28"
            },
            headers=auth_headers
        )

        assert response.status_code == 422
