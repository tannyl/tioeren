"""Tests for amount pattern functionality."""

from datetime import date
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.budget_post import BudgetPost, BudgetPostDirection
from api.models.budget import Budget
from api.models.user import User
from api.models.amount_pattern import AmountPattern
from api.services.budget_post_service import expand_amount_patterns_to_occurrences


class TestAmountPatternModel:
    """Test amount pattern model and relationships."""

    def test_create_amount_pattern(self, db: Session):
        """Test creating an amount pattern."""
        # Create necessary parent objects
        user = User(email="amount_patterns_test@example.com", password_hash="dummy")
        db.add(user)
        db.commit()

        budget = Budget(name="Test Budget", owner_id=user.id)
        db.add(budget)
        db.commit()

        budget_post = BudgetPost(
            budget_id=budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )
        db.add(budget_post)
        db.commit()

        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=50000,  # 500 kr
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 31),
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 15,
            },
        )
        db.add(pattern)
        db.commit()
        db.refresh(pattern)

        assert pattern.id is not None
        assert pattern.amount == 50000
        assert pattern.start_date == date(2026, 2, 1)
        assert pattern.end_date == date(2026, 12, 31)

    def test_budget_post_relationship(self, db: Session):
        """Test relationship between budget post and amount patterns."""
        # Create necessary parent objects
        user = User(email="test2@example.com", password_hash="dummy")
        db.add(user)
        db.commit()

        budget = Budget(name="Test Budget 2", owner_id=user.id)
        db.add(budget)
        db.commit()

        budget_post = BudgetPost(
            budget_id=budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )
        db.add(budget_post)
        db.commit()

        pattern1 = AmountPattern(
            budget_post_id=budget_post.id,
            amount=30000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={"type": "weekly", "interval": 1, "weekday": 4},
        )
        pattern2 = AmountPattern(
            budget_post_id=budget_post.id,
            amount=35000,
            start_date=date(2026, 6, 1),
            end_date=None,
            recurrence_pattern={"type": "weekly", "interval": 1, "weekday": 4},
        )
        db.add(pattern1)
        db.add(pattern2)
        db.commit()

        # Refresh budget_post to load relationship
        db.refresh(budget_post)

        assert len(budget_post.amount_patterns) == 2
        assert pattern1 in budget_post.amount_patterns
        assert pattern2 in budget_post.amount_patterns

    def test_cascade_delete(self, db: Session):
        """Test that deleting budget post cascades to amount patterns."""
        # Create necessary parent objects
        user = User(email="test3@example.com", password_hash="dummy")
        db.add(user)
        db.commit()

        budget = Budget(name="Test Budget 3", owner_id=user.id)
        db.add(budget)
        db.commit()

        budget_post = BudgetPost(
            budget_id=budget.id,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )
        db.add(budget_post)
        db.commit()

        pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=10000,
            start_date=date(2026, 2, 1),
            end_date=None,
        )
        db.add(pattern)
        db.commit()
        pattern_id = pattern.id

        # Delete budget post
        db.delete(budget_post)
        db.commit()

        # Pattern should also be deleted
        deleted_pattern = db.query(AmountPattern).filter(AmountPattern.id == pattern_id).first()
        assert deleted_pattern is None


# NOTE: API tests are covered by existing budget post API tests
# which now test amount_patterns automatically


class TestOccurrenceExpansionWithPatterns:
    """Test occurrence expansion with multiple amount patterns."""

    def test_expand_single_pattern(self):
        """Test expanding occurrences from a single pattern."""
        budget_post = BudgetPost(
            id=uuid4(),
            budget_id=uuid4(),
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )

        pattern = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=50000,
            start_date=date(2026, 2, 1),
            end_date=None,
            recurrence_pattern={
                "type": "weekly",
                "interval": 1,
                "weekday": 0,  # Monday
            },
        )
        # Add pattern to budget_post's relationship
        budget_post.amount_patterns = [pattern]

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28),
        )

        # February 2026 has 4 Mondays
        assert len(occurrences) == 4
        # All should have the same amount
        assert all(amount == 50000 for _, amount in occurrences)

    def test_expand_multiple_patterns_no_overlap(self):
        """Test expanding occurrences from multiple non-overlapping patterns."""
        budget_post = BudgetPost(
            id=uuid4(),
            budget_id=uuid4(),
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )

        pattern1 = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=30000,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            recurrence_pattern={
                "type": "weekly",
                "interval": 1,
                "weekday": 0,  # Monday
            },
        )
        pattern2 = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=40000,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            recurrence_pattern={
                "type": "weekly",
                "interval": 1,
                "weekday": 0,  # Monday
            },
        )
        budget_post.amount_patterns = [pattern1, pattern2]

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 3, 31),
        )

        # February 2026 has 4 Mondays, March has 5 Mondays
        assert len(occurrences) == 9

        # First 4 should be 30000
        february_occurrences = [occ for occ in occurrences if occ[0].month == 2]
        assert len(february_occurrences) == 4
        assert all(amount == 30000 for _, amount in february_occurrences)

        # Last 5 should be 40000
        march_occurrences = [occ for occ in occurrences if occ[0].month == 3]
        assert len(march_occurrences) == 5
        assert all(amount == 40000 for _, amount in march_occurrences)

    def test_expand_salary_increase_scenario(self):
        """Test realistic scenario: salary increase mid-year."""
        budget_post = BudgetPost(
            id=uuid4(),
            budget_id=uuid4(),
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )

        # Salary before increase
        pattern1 = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=4500000,  # 45,000 kr
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 25,  # Salary on 25th
            },
        )
        # Salary after increase
        pattern2 = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=4800000,  # 48,000 kr
            start_date=date(2026, 6, 1),
            end_date=None,
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 25,
            },
        )
        budget_post.amount_patterns = [pattern1, pattern2]

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 12, 31),
        )

        # 11 months = 11 salary payments (Feb-Dec)
        assert len(occurrences) == 11

        # First 4 months (Feb-May) should be 45,000 kr
        first_half = [occ for occ in occurrences if 2 <= occ[0].month <= 5]
        assert len(first_half) == 4
        assert all(amount == 4500000 for _, amount in first_half)

        # Last 7 months (Jun-Dec) should be 48,000 kr
        second_half = [occ for occ in occurrences if occ[0].month >= 6]
        assert len(second_half) == 7
        assert all(amount == 4800000 for _, amount in second_half)

    def test_expand_seasonal_electricity_scenario(self):
        """Test realistic scenario: seasonal electricity costs."""
        budget_post = BudgetPost(
            id=uuid4(),
            budget_id=uuid4(),
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )

        # Winter months (higher consumption)
        winter_pattern = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=150000,  # 1,500 kr
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 31),
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 1,
            },
        )
        # Summer months (lower consumption)
        summer_pattern = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=80000,  # 800 kr
            start_date=date(2026, 4, 1),
            end_date=date(2026, 9, 30),
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 1,
            },
        )
        # Winter again
        winter2_pattern = AmountPattern(
            id=uuid4(),
            budget_post_id=budget_post.id,
            amount=150000,  # 1,500 kr
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            recurrence_pattern={
                "type": "monthly_fixed",
                "interval": 1,
                "day_of_month": 1,
            },
        )
        budget_post.amount_patterns = [winter_pattern, summer_pattern, winter2_pattern]

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 12, 31),
        )

        # 11 months = 11 bills (Feb-Dec)
        assert len(occurrences) == 11

        # Feb-Mar: winter rates
        winter1 = [occ for occ in occurrences if 2 <= occ[0].month <= 3]
        assert len(winter1) == 2
        assert all(amount == 150000 for _, amount in winter1)

        # Apr-Sep: summer rates
        summer = [occ for occ in occurrences if 4 <= occ[0].month <= 9]
        assert len(summer) == 6
        assert all(amount == 80000 for _, amount in summer)

        # Oct-Dec: winter rates again
        winter2 = [occ for occ in occurrences if 10 <= occ[0].month <= 12]
        assert len(winter2) == 3
        assert all(amount == 150000 for _, amount in winter2)

    def test_empty_patterns_returns_empty(self):
        """Test that expansion with no patterns returns empty list."""
        budget_post = BudgetPost(
            id=uuid4(),
            budget_id=uuid4(),
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            direction=BudgetPostDirection.EXPENSE,
            accumulate=False,
            container_ids=[str(uuid4())],  # Dummy account for expense
        )
        # No amount_patterns - should return empty
        budget_post.amount_patterns = []

        occurrences = expand_amount_patterns_to_occurrences(
            budget_post,
            date(2026, 2, 1),
            date(2026, 2, 28),
        )

        assert len(occurrences) == 0
