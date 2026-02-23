"""Tests for forecast service."""

import uuid
from datetime import date
from calendar import monthrange

import pytest
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.transaction import Transaction, TransactionStatus
from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection
from api.models.amount_pattern import AmountPattern
from api.services.forecast_service import (
    calculate_forecast,
    get_current_balance,
)


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
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account



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
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(savings)
    db.commit()

    balance = get_current_balance(db, test_budget.id)
    # Should only include test_account (normal), not savings
    assert balance == 1000000


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
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test forecast with monthly recurring budget posts."""
    # Create salary (income)
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Løn"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Create rent (expense)
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent])
    db.flush()

    # Create amount patterns - amounts are positive in new model
    salary_pattern = AmountPattern(
        budget_post_id=salary.id,
        amount=2500000,  # 25000 kr (positive)
        start_date=date(2026, 2, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    rent_pattern = AmountPattern(
        budget_post_id=rent.id,
        amount=800000,  # 8000 kr (positive - direction determines sign)
        start_date=date(2026, 2, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([salary_pattern, rent_pattern])
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
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test forecast with various recurrence patterns."""
    today = date.today()

    # Monthly salary
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Løn"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Monthly rent
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Quarterly insurance (only occurs in specific months)
    insurance = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Forsikring"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent, insurance])
    db.flush()

    # Create amount patterns - amounts are positive in new model
    salary_pattern = AmountPattern(
        budget_post_id=salary.id,
        amount=2500000,  # 25000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    rent_pattern = AmountPattern(
        budget_post_id=rent.id,
        amount=800000,  # 8000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    insurance_pattern = AmountPattern(
        budget_post_id=insurance.id,
        amount=120000,  # 1200 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},  # Monthly (same as rent)
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([salary_pattern, rent_pattern, insurance_pattern])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=12)

    assert len(result.projections) == 12

    # Check that all expenses appear every month (insurance is monthly now, not quarterly)
    for i, projection in enumerate(result.projections):
        # Base monthly income and expense (including insurance which is also monthly)
        expected_income = 2500000
        expected_expense = -800000 + (-120000)  # Rent + Insurance every month

        assert projection.expected_income == expected_income
        assert projection.expected_expenses == expected_expense


def test_calculate_forecast_lowest_point_identification(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test that lowest balance point is correctly identified."""
    # Create scenario where balance dips in the middle
    # Starting balance: 1,000,000 (10,000 kr)

    # Monthly income on day 15
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Løn"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Large expense on day 1 of each month
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([salary, rent])
    db.flush()

    # Create amount patterns - amounts are positive in new model
    today = date.today()
    salary_pattern = AmountPattern(
        budget_post_id=salary.id,
        amount=2500000,  # 25000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 15, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    rent_pattern = AmountPattern(
        budget_post_id=rent.id,
        amount=2000000,  # 20000 kr (positive, more than we have)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([salary_pattern, rent_pattern])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=6)

    # First month: 1,000,000 + 2,500,000 - 2,000,000 = 1,500,000
    # Each subsequent month adds net +500,000

    # The first month should have the lowest balance initially
    # But balance should recover and grow
    assert result.lowest_point["balance"] < 1500000


def test_calculate_forecast_next_large_expense_detection(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test detection of next large expense."""
    today = date.today()

    # Small monthly expense
    groceries = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Mad"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
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
        category_path=["Udgift", "Forsikring"],
        display_order=[0, 1],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([groceries, large_expense])
    db.flush()

    # Create amount patterns - amounts are positive in new model
    groceries_pattern = AmountPattern(
        budget_post_id=groceries.id,
        amount=300000,  # 3000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    expense_date = date(year, month, 15)
    large_expense_pattern = AmountPattern(
        budget_post_id=large_expense.id,
        amount=1200000,  # 12000 kr (positive, large)
        start_date=expense_date,
        end_date=expense_date,
        recurrence_pattern={"type": "once", "date": f"{year}-{month:02d}-15", "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([groceries_pattern, large_expense_pattern])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=6)

    # Should identify the large insurance payment as next large expense
    assert result.next_large_expense is not None
    assert result.next_large_expense["name"] == "Forsikring"
    assert result.next_large_expense["amount"] == -1200000


def test_calculate_forecast_respects_budget_post_type(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test that forecast respects budget post type for amount calculation."""
    # FIXED type
    fixed_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Fast"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # CEILING type
    ceiling_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Loft"],
        display_order=[0, 1],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.CEILING,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([fixed_post, ceiling_post])
    db.flush()

    # Create amount patterns - amounts are positive in new model
    today = date.today()
    fixed_pattern = AmountPattern(
        budget_post_id=fixed_post.id,
        amount=100000,  # 1000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    ceiling_pattern = AmountPattern(
        budget_post_id=ceiling_post.id,
        amount=200000,  # 2000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([fixed_pattern, ceiling_pattern])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Expected expenses: -100000 (fixed) + -200000 (ceiling) = -300000
    assert result.projections[0].expected_expenses == -300000


def test_calculate_forecast_handles_year_boundary(
    db: Session, test_budget: Budget, test_account: Account, test_user: User
):
    """Test that forecast correctly handles year transitions."""
    # Create a budget post that occurs monthly
    monthly_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Månedlig"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        account_ids=[str(test_account.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add(monthly_post)
    db.flush()

    # Create amount pattern - amounts are positive in new model
    today = date.today()
    monthly_pattern = AmountPattern(
        budget_post_id=monthly_post.id,
        amount=100000,  # 1000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(monthly_pattern)
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
