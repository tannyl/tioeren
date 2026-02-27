"""Tests for archived budget posts functionality."""

import pytest
from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session

from api.models.budget import Budget
from api.models.container import Container, ContainerType
from api.models.budget_post import BudgetPost, BudgetPostDirection
from api.models.user import User
from api.services.budget_post_service import (
    create_budget_post,
    create_archived_budget_post,
    get_archived_budget_posts,
    get_archived_budget_post_by_id,
)


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="archive@example.com",
        password_hash="dummy_hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_budget(db: Session, test_user: User) -> Budget:
    """Create a test budget."""
    budget = Budget(
        name="Archive Test Budget",
        owner_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget




@pytest.fixture
def cashbox_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a CASHBOX container."""
    container = Container(
        budget_id=test_budget.id,
        name="Main Container",
        type=ContainerType.CASHBOX,
        starting_balance=100000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def sample_budget_post(
    db: Session, test_budget: Budget, test_user: User, cashbox_container: Account
) -> BudgetPost:
    """Create a sample budget post for archiving."""
    budget_post, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        container_ids=[str(cashbox_container.id)],  # Replaced counterparty
        amount_patterns=[
            {
                "amount": 1000000,  # 10,000 kr rent
                "start_date": "2026-01-01",
                "end_date": None,
                "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1},
                "container_ids": [str(cashbox_container.id)],
            }
        ],
    )
    return budget_post


class TestArchivedBudgetPostCreation:
    """Test creating archived budget posts."""

    def test_create_archived_budget_post(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Create an archived budget post for a period."""
        archived_post = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=2,  # February
            user_id=test_user.id,
        )

        assert archived_post is not None
        assert archived_post.budget_id == test_budget.id
        assert archived_post.budget_post_id == sample_budget_post.id
        assert archived_post.period_year == 2026
        assert archived_post.period_month == 2
        assert archived_post.direction == sample_budget_post.direction
        assert archived_post.category_path == sample_budget_post.category_path

    def test_archived_post_expands_occurrences(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Archived budget post contains expanded occurrences."""
        archived_post = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=2,
            user_id=test_user.id,
        )

        # Should have 1 occurrence on Feb 1, 2026 (monthly_fixed on day 1)
        assert len(archived_post.amount_occurrences) == 1
        assert archived_post.amount_occurrences[0].date == date(2026, 2, 1)
        assert archived_post.amount_occurrences[0].amount == 1000000

    def test_archived_post_expands_multiple_occurrences(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Account
    ):
        """Archived post with weekly pattern expands to multiple occurrences."""
        # Create a budget post with weekly pattern
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Transport"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],  # Replaced counterparty
            amount_patterns=[
                {
                    "amount": 50000,  # 500 kr weekly
                    "start_date": "2026-02-01",
                    "end_date": None,
                    "recurrence_pattern": {"type": "weekly", "weekday": 0},  # Every Monday
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )

        archived_post = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=budget_post,
            period_year=2026,
            period_month=2,
            user_id=test_user.id,
        )

        # February 2026 has 4 Mondays (2, 9, 16, 23)
        assert len(archived_post.amount_occurrences) == 4
        dates = [occ.date for occ in archived_post.amount_occurrences]
        assert date(2026, 2, 2) in dates
        assert date(2026, 2, 9) in dates
        assert date(2026, 2, 16) in dates
        assert date(2026, 2, 23) in dates


class TestArchivedBudgetPostQueries:
    """Test querying archived budget posts."""

    def test_get_archived_posts_for_budget(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Get all archived posts for a budget."""
        # Create archived posts for different periods
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=1,
            user_id=test_user.id,
        )
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=2,
            user_id=test_user.id,
        )

        archived_posts = get_archived_budget_posts(db=db, budget_id=test_budget.id)

        assert len(archived_posts) == 2
        # Should be ordered by period descending (Feb before Jan)
        assert archived_posts[0].period_year == 2026
        assert archived_posts[0].period_month == 2
        assert archived_posts[1].period_month == 1

    def test_get_archived_posts_filtered_by_year(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Filter archived posts by year."""
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2025,
            period_month=12,
            user_id=test_user.id,
        )
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=1,
            user_id=test_user.id,
        )

        archived_posts = get_archived_budget_posts(db=db, budget_id=test_budget.id, period_year=2026)

        assert len(archived_posts) == 1
        assert archived_posts[0].period_year == 2026

    def test_get_archived_posts_filtered_by_month(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Filter archived posts by month."""
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=1,
            user_id=test_user.id,
        )
        create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=2,
            user_id=test_user.id,
        )

        archived_posts = get_archived_budget_posts(
            db=db, budget_id=test_budget.id, period_year=2026, period_month=2
        )

        assert len(archived_posts) == 1
        assert archived_posts[0].period_month == 2

    def test_get_archived_post_by_id(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Get a specific archived post by ID."""
        created_archived = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=3,
            user_id=test_user.id,
        )

        retrieved_archived = get_archived_budget_post_by_id(
            db=db, archived_post_id=created_archived.id, budget_id=test_budget.id
        )

        assert retrieved_archived is not None
        assert retrieved_archived.id == created_archived.id
        assert retrieved_archived.period_year == 2026
        assert retrieved_archived.period_month == 3
        assert len(retrieved_archived.amount_occurrences) > 0

    def test_get_archived_post_wrong_budget(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Cannot get archived post from different budget."""
        created_archived = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=4,
            user_id=test_user.id,
        )

        # Try to get with wrong budget ID
        wrong_budget_id = uuid4()
        retrieved_archived = get_archived_budget_post_by_id(
            db=db, archived_post_id=created_archived.id, budget_id=wrong_budget_id
        )

        assert retrieved_archived is None


class TestArchivedBudgetPostImmutability:
    """Test that archived budget posts preserve snapshots."""

    def test_archived_post_preserved_after_budget_post_update(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Archived post is not affected by updates to the original budget post."""
        # Create archived post
        archived_post = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=5,
            user_id=test_user.id,
        )

        original_occurrences = len(archived_post.amount_occurrences)

        # Update the original budget post (change category_path)
        sample_budget_post.category_path = ["Udgift", "Transport"]
        db.commit()

        # Re-fetch archived post
        db.refresh(archived_post)

        # Archived post should be unchanged
        assert archived_post.category_path == ["Udgift", "Husleje"]
        assert len(archived_post.amount_occurrences) == original_occurrences

    def test_archived_post_preserved_after_budget_post_deletion(
        self, db: Session, test_budget: Budget, test_user: User, sample_budget_post: BudgetPost
    ):
        """Archived post is preserved even if original budget post is deleted."""
        from datetime import datetime, UTC

        # Create archived post
        archived_post = create_archived_budget_post(
            db=db,
            budget_id=test_budget.id,
            budget_post=sample_budget_post,
            period_year=2026,
            period_month=6,
            user_id=test_user.id,
        )

        archived_post_id = archived_post.id

        # Soft delete the original budget post
        sample_budget_post.deleted_at = datetime.now(UTC)
        db.commit()

        # Archived post should still exist
        retrieved = get_archived_budget_post_by_id(db=db, archived_post_id=archived_post_id, budget_id=test_budget.id)

        assert retrieved is not None
        assert retrieved.budget_post_id == sample_budget_post.id  # Reference preserved
        assert len(retrieved.amount_occurrences) > 0
