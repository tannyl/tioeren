"""Tests for forecast service."""

import uuid
from datetime import date, timedelta
from calendar import monthrange

import pytest
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.transaction import Transaction, TransactionStatus
from api.models.category import Category
from api.models.budget_post import BudgetPost, BudgetPostType
from api.services.forecast_service import (
    calculate_forecast,
    generate_occurrences,
    get_current_balance,
)
from api.services.auth import hash_password


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        email="forecast@example.com",
        password_hash=hash_password("SecurePassword123!"),
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_budget(db: Session, test_user: User):
    """Create a test budget."""
    budget = Budget(
        name="Forecast Budget",
        owner_id=test_user.id,
        warning_threshold=100000,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@pytest.fixture
def test_account(db: Session, test_budget: Budget, test_user: User):
    """Create a test account."""
    account = Account(
        budget_id=test_budget.id,
        name="Checking",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        starting_balance=1000000,  # 10,000 kr
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_category(db: Session, test_budget: Budget, test_user: User):
    """Create a test category."""
    category = Category(
        budget_id=test_budget.id,
        name="Expenses",
        parent_id=None,
        is_system=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def test_get_current_balance_empty(db: Session, test_budget: Budget, test_account: Account):
    """Test getting current balance with no transactions."""
    balance = get_current_balance(db, test_budget.id)
    # Should equal starting balance
    assert balance == 1000000


def test_get_current_balance_with_transactions(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test getting current balance with transactions."""
    # Add some transactions
    trans1 = Transaction(
        account_id=test_account.id,
        date=date.today(),
        amount=50000,  # +500 kr
        description="Income",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    trans2 = Transaction(
        account_id=test_account.id,
        date=date.today(),
        amount=-20000,  # -200 kr
        description="Expense",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    db.add_all([trans1, trans2])
    db.commit()

    balance = get_current_balance(db, test_budget.id)
    # 1000000 + 50000 - 20000 = 1030000
    assert balance == 1030000


def test_get_current_balance_only_normal_accounts(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test that current balance only includes normal accounts."""
    # Add a savings account
    savings = Account(
        budget_id=test_budget.id,
        name="Savings",
        purpose=AccountPurpose.SAVINGS,
        datasource=AccountDatasource.BANK,
        starting_balance=5000000,  # 50,000 kr
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(savings)
    db.commit()

    balance = get_current_balance(db, test_budget.id)
    # Should only include test_account (normal), not savings
    assert balance == 1000000


def test_generate_occurrences_monthly(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences for monthly recurrence."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Rent",
        type=BudgetPostType.FIXED,
        amount_min=-800000,  # -8000 kr
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    month_date = date(2026, 3, 1)
    occurrences = generate_occurrences(budget_post, month_date)

    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 3, 1)
    assert occurrences[0]["amount"] == -800000


def test_generate_occurrences_monthly_day_15(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences for monthly recurrence on day 15."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Salary",
        type=BudgetPostType.FIXED,
        amount_min=2500000,  # +25000 kr
        recurrence_pattern={"type": "monthly", "day": 15},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    month_date = date(2026, 4, 1)
    occurrences = generate_occurrences(budget_post, month_date)

    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 4, 15)
    assert occurrences[0]["amount"] == 2500000


def test_generate_occurrences_quarterly(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences for quarterly recurrence."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Insurance",
        type=BudgetPostType.FIXED,
        amount_min=-120000,  # -1200 kr
        recurrence_pattern={"type": "quarterly", "months": [3, 6, 9, 12], "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Test quarter month (March)
    march = date(2026, 3, 1)
    occurrences = generate_occurrences(budget_post, march)
    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 3, 1)

    # Test non-quarter month (April)
    april = date(2026, 4, 1)
    occurrences = generate_occurrences(budget_post, april)
    assert len(occurrences) == 0


def test_generate_occurrences_yearly(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences for yearly recurrence."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Annual Fee",
        type=BudgetPostType.FIXED,
        amount_min=-50000,  # -500 kr
        recurrence_pattern={"type": "yearly", "month": 6, "day": 15},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Test target month (June)
    june = date(2026, 6, 1)
    occurrences = generate_occurrences(budget_post, june)
    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 6, 15)

    # Test other month
    march = date(2026, 3, 1)
    occurrences = generate_occurrences(budget_post, march)
    assert len(occurrences) == 0


def test_generate_occurrences_once(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences for one-time event."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Vacation",
        type=BudgetPostType.FIXED,
        amount_min=-1000000,  # -10000 kr
        recurrence_pattern={"type": "once", "date": "2026-07-15"},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Test target month
    july = date(2026, 7, 1)
    occurrences = generate_occurrences(budget_post, july)
    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 7, 15)

    # Test other month
    august = date(2026, 8, 1)
    occurrences = generate_occurrences(budget_post, august)
    assert len(occurrences) == 0


def test_generate_occurrences_no_pattern(test_category: Category, test_account: Account, test_user: User):
    """Test generating occurrences with no pattern defaults to monthly."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Default",
        type=BudgetPostType.FIXED,
        amount_min=-10000,
        recurrence_pattern=None,
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    month_date = date(2026, 5, 1)
    occurrences = generate_occurrences(budget_post, month_date)

    # Should default to monthly on day 1
    assert len(occurrences) == 1
    assert occurrences[0]["date"] == date(2026, 5, 1)


def test_generate_occurrences_ceiling_type(test_category: Category, test_account: Account, test_user: User):
    """Test that ceiling type uses amount_max."""
    budget_post = BudgetPost(
        budget_id=test_category.budget_id,
        category_id=test_category.id,
        name="Groceries",
        type=BudgetPostType.CEILING,
        amount_min=-200000,
        amount_max=-300000,  # Max 3000 kr
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    month_date = date(2026, 5, 1)
    occurrences = generate_occurrences(budget_post, month_date)

    assert len(occurrences) == 1
    # Should use amount_max for ceiling type
    assert occurrences[0]["amount"] == -300000


def test_calculate_forecast_no_budget_posts(db: Session, test_budget: Budget, test_account: Account):
    """Test forecast with no budget posts (flat projection)."""
    result = calculate_forecast(db, test_budget.id, months=3)

    assert len(result.projections) == 3

    # All months should have same balance (no changes)
    for projection in result.projections:
        assert projection.start_balance == 1000000
        assert projection.expected_income == 0
        assert projection.expected_expenses == 0
        assert projection.end_balance == 1000000

    # Lowest point should be current balance
    assert result.lowest_point["balance"] == 1000000

    # No large expenses
    assert result.next_large_expense is None


def test_calculate_forecast_with_monthly_income_and_expense(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test forecast with monthly recurring budget posts."""
    # Create salary (income)
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Salary",
        type=BudgetPostType.FIXED,
        amount_min=2500000,  # +25000 kr
        to_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Create rent (expense)
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Rent",
        type=BudgetPostType.FIXED,
        amount_min=-800000,  # -8000 kr
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=3)

    assert len(result.projections) == 3

    # First month
    proj1 = result.projections[0]
    assert proj1.start_balance == 1000000
    assert proj1.expected_income == 2500000
    assert proj1.expected_expenses == -800000
    assert proj1.end_balance == 1000000 + 2500000 - 800000  # 2,700,000

    # Second month
    proj2 = result.projections[1]
    assert proj2.start_balance == proj1.end_balance
    assert proj2.expected_income == 2500000
    assert proj2.expected_expenses == -800000
    assert proj2.end_balance == proj1.end_balance + 2500000 - 800000  # 4,400,000

    # Third month
    proj3 = result.projections[2]
    assert proj3.start_balance == proj2.end_balance
    assert proj3.end_balance == proj2.end_balance + 2500000 - 800000  # 6,100,000


def test_calculate_forecast_with_mixed_recurrence_patterns(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test forecast with various recurrence patterns."""
    today = date.today()

    # Monthly salary
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Salary",
        type=BudgetPostType.FIXED,
        amount_min=2500000,  # +25000 kr
        to_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Monthly rent
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Rent",
        type=BudgetPostType.FIXED,
        amount_min=-800000,  # -8000 kr
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Quarterly insurance (only occurs in specific months)
    insurance = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Insurance",
        type=BudgetPostType.FIXED,
        amount_min=-120000,  # -1200 kr
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "quarterly", "months": [3, 6, 9, 12], "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent, insurance])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=12)

    assert len(result.projections) == 12

    # Check that quarterly insurance only appears in specific months
    for i, projection in enumerate(result.projections):
        # Calculate which month this is
        year = today.year
        month = today.month + i
        while month > 12:
            month -= 12
            year += 1

        # Base monthly income and expense
        expected_income = 2500000
        base_expense = -800000

        if month in [3, 6, 9, 12]:
            # Quarter months should include insurance
            expected_expense = base_expense + (-120000)
        else:
            expected_expense = base_expense

        assert projection.expected_income == expected_income
        assert projection.expected_expenses == expected_expense


def test_calculate_forecast_lowest_point_identification(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test that lowest balance point is correctly identified."""
    # Create scenario where balance dips in the middle
    # Starting balance: 1,000,000 (10,000 kr)

    # Monthly income on day 15
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Salary",
        type=BudgetPostType.FIXED,
        amount_min=2500000,  # +25000 kr
        to_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 15},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Large expense on day 1 of each month
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Rent",
        type=BudgetPostType.FIXED,
        amount_min=-2000000,  # -20000 kr (more than we have)
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=6)

    # First month: 1,000,000 + 2,500,000 - 2,000,000 = 1,500,000
    # Each subsequent month adds net +500,000

    # The first month should have the lowest balance initially
    # But balance should recover and grow
    assert result.lowest_point["balance"] < 1500000


def test_calculate_forecast_next_large_expense_detection(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test detection of next large expense."""
    today = date.today()

    # Small monthly expense
    groceries = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Groceries",
        type=BudgetPostType.FIXED,
        amount_min=-300000,  # -3000 kr
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Large expense in second month
    year = today.year
    month = today.month + 1
    if month > 12:
        month -= 12
        year += 1

    large_expense = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Insurance Payment",
        type=BudgetPostType.FIXED,
        amount_min=-1200000,  # -12000 kr (large)
        from_account_ids=[str(test_account.id)],
        recurrence_pattern={"type": "once", "date": f"{year}-{month:02d}-15"},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([groceries, large_expense])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=6)

    # Should identify the large insurance payment as next large expense
    assert result.next_large_expense is not None
    assert result.next_large_expense["name"] == "Insurance Payment"
    assert result.next_large_expense["amount"] == -1200000


def test_calculate_forecast_respects_budget_post_type(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test that forecast respects budget post type for amount calculation."""
    # FIXED type - uses amount_min
    fixed_post = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Fixed Expense",
        type=BudgetPostType.FIXED,
        amount_min=-100000,
        amount_max=None,
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # CEILING type - uses amount_max
    ceiling_post = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Ceiling Expense",
        type=BudgetPostType.CEILING,
        amount_min=-50000,
        amount_max=-200000,
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # ROLLING type - uses amount_min
    rolling_post = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Rolling Budget",
        type=BudgetPostType.ROLLING,
        amount_min=-75000,
        amount_max=None,
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([fixed_post, ceiling_post, rolling_post])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Expected expenses: -100000 (fixed) + -200000 (ceiling max) + -75000 (rolling) = -375000
    assert result.projections[0].expected_expenses == -375000


def test_calculate_forecast_handles_year_boundary(
    db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User
):
    """Test that forecast correctly handles year transitions."""
    # Create a budget post that occurs monthly
    monthly_post = BudgetPost(
        budget_id=test_budget.id,
        category_id=test_category.id,
        name="Monthly",
        type=BudgetPostType.FIXED,
        amount_min=-100000,
        recurrence_pattern={"type": "monthly", "day": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add(monthly_post)
    db.commit()

    # Request 15 months to ensure year transition
    result = calculate_forecast(db, test_budget.id, months=15)

    assert len(result.projections) == 15

    # Each month should have the same expense
    for projection in result.projections:
        assert projection.expected_expenses == -100000

    # Verify month strings are correctly formatted across year boundary
    today = date.today()
    for i, projection in enumerate(result.projections):
        year = today.year
        month = today.month + i
        while month > 12:
            month -= 12
            year += 1

        expected_month_str = f"{year}-{month:02d}"
        assert projection.month == expected_month_str
