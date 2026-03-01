"""Tests for forecast service."""

import uuid
from datetime import date
from calendar import monthrange

import pytest
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.container import Container, ContainerType
from api.models.transaction import Transaction, TransactionStatus
from api.models.budget_post import BudgetPost, BudgetPostDirection
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
def test_container(db: Session, test_budget: Budget, test_user: User):
    """Create a test container."""
    container = Container(
        budget_id=test_budget.id,
        name="Checking",
        type=ContainerType.CASHBOX,
        starting_balance=1000000,  # 10,000 kr
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container



def test_get_current_balance_empty(db: Session, test_budget: Budget, test_container: Container):
    """Test getting current balance with no transactions."""
    balance = get_current_balance(db, test_budget.id)
    # Should equal starting balance
    assert balance == 1000000


def test_get_current_balance_with_transactions(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test getting current balance with transactions."""
    # Add some transactions
    trans1 = Transaction(
        container_id=test_container.id,
        date=date.today(),
        amount=50000,  # +500 kr
        description="Income",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    trans2 = Transaction(
        container_id=test_container.id,
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
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that current balance only includes normal accounts."""
    # Add a savings container
    savings = Container(
        budget_id=test_budget.id,
        name="Savings",
        type=ContainerType.PIGGYBANK,
        starting_balance=5000000,  # 50,000 kr
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(savings)
    db.commit()

    balance = get_current_balance(db, test_budget.id)
    # Should only include test_container (normal), not savings
    assert balance == 1000000


def test_calculate_forecast_no_budget_posts(db: Session, test_budget: Budget, test_container: Container):
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
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test forecast with monthly recurring budget posts."""
    # Create salary (income)
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Løn"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Create rent (expense)
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test forecast with various recurrence patterns."""
    today = date.today()

    # Monthly salary
    salary = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Løn"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Monthly rent
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Quarterly insurance (only occurs in specific months)
    insurance = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Forsikring"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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
    db: Session, test_budget: Budget, test_container: Container, test_user: User
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
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Large expense on day 1 of each month
    rent = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test detection of next large expense."""
    today = date.today()

    # Small monthly expense
    groceries = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Mad"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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


def test_calculate_forecast_multiple_expense_posts(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that forecast correctly aggregates multiple expense budget posts."""
    expense_post_1 = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    expense_post_2 = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Mad"],
        display_order=[0, 1],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([expense_post_1, expense_post_2])
    db.flush()

    today = date.today()
    pattern_1 = AmountPattern(
        budget_post_id=expense_post_1.id,
        amount=100000,  # 1000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    pattern_2 = AmountPattern(
        budget_post_id=expense_post_2.id,
        amount=200000,  # 2000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([pattern_1, pattern_2])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Expected expenses: -100000 + -200000 = -300000
    assert result.projections[0].expected_expenses == -300000


def test_calculate_forecast_handles_year_boundary(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that forecast correctly handles year transitions."""
    # Create a budget post that occurs monthly
    monthly_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Månedlig"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
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


def test_calculate_forecast_root_level_filtering(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that forecast only uses root-level posts (ceiling semantics)."""
    # Create parent "Bolig" post with 10000 kr
    parent_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Bolig"],
        display_order=[0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    # Create child "Bolig > Husleje" post with 8000 kr
    child_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Bolig", "Husleje"],
        display_order=[0, 0],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    db.add_all([parent_post, child_post])
    db.flush()

    today = date.today()
    # Parent pattern (ceiling amount includes child)
    parent_pattern = AmountPattern(
        budget_post_id=parent_post.id,
        amount=1000000,  # 10000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    # Child pattern
    child_pattern = AmountPattern(
        budget_post_id=child_post.id,
        amount=800000,  # 8000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        container_ids=[str(test_container.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([parent_pattern, child_pattern])
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Should only count parent's 10000 kr, not parent + child (18000 kr)
    assert result.projections[0].expected_expenses == -1000000


def test_calculate_forecast_transfer_pengekasse_to_sparegris(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that pengekasse → sparegris transfers reduce balance."""
    # Create a piggybank container
    sparegris = Container(
        budget_id=test_budget.id,
        name="Sparegris",
        type=ContainerType.PIGGYBANK,
        starting_balance=0,
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(sparegris)
    db.flush()

    # Create transfer post: pengekasse → sparegris
    transfer_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=None,
        display_order=None,
        direction=BudgetPostDirection.TRANSFER,
        accumulate=False,
        container_ids=None,
        transfer_from_container_id=test_container.id,  # cashbox
        transfer_to_container_id=sparegris.id,  # piggybank
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_post)
    db.flush()

    today = date.today()
    transfer_pattern = AmountPattern(
        budget_post_id=transfer_post.id,
        amount=50000,  # 500 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 15, "interval": 1},
        container_ids=None,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_pattern)
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Transfer should reduce balance (treated as expense)
    assert result.projections[0].expected_income == 0
    assert result.projections[0].expected_expenses == -50000
    assert result.projections[0].end_balance == 1000000 - 50000  # 950000


def test_calculate_forecast_transfer_sparegris_to_pengekasse(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that sparegris → pengekasse transfers increase balance."""
    # Create a piggybank container
    sparegris = Container(
        budget_id=test_budget.id,
        name="Sparegris",
        type=ContainerType.PIGGYBANK,
        starting_balance=10000000,  # 100000 kr
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(sparegris)
    db.flush()

    # Create transfer post: sparegris → pengekasse
    transfer_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=None,
        display_order=None,
        direction=BudgetPostDirection.TRANSFER,
        accumulate=False,
        container_ids=None,
        transfer_from_container_id=sparegris.id,  # piggybank
        transfer_to_container_id=test_container.id,  # cashbox
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_post)
    db.flush()

    today = date.today()
    transfer_pattern = AmountPattern(
        budget_post_id=transfer_post.id,
        amount=30000,  # 300 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 20, "interval": 1},
        container_ids=None,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_pattern)
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Transfer should increase balance (treated as income)
    assert result.projections[0].expected_income == 30000
    assert result.projections[0].expected_expenses == 0
    assert result.projections[0].end_balance == 1000000 + 30000  # 1030000


def test_calculate_forecast_transfer_pengekasse_to_pengekasse(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that pengekasse → pengekasse transfers are net-zero."""
    # Create another cashbox container
    cashbox2 = Container(
        budget_id=test_budget.id,
        name="Cashbox 2",
        type=ContainerType.CASHBOX,
        starting_balance=50000,
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(cashbox2)
    db.flush()

    # Create transfer post: pengekasse → pengekasse
    transfer_post = BudgetPost(
        budget_id=test_budget.id,
        category_path=None,
        display_order=None,
        direction=BudgetPostDirection.TRANSFER,
        accumulate=False,
        container_ids=None,
        transfer_from_container_id=test_container.id,  # cashbox
        transfer_to_container_id=cashbox2.id,  # cashbox
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_post)
    db.flush()

    today = date.today()
    transfer_pattern = AmountPattern(
        budget_post_id=transfer_post.id,
        amount=20000,  # 200 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 10, "interval": 1},
        container_ids=None,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transfer_pattern)
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Transfer should be net-zero (both income and expense are 0)
    assert result.projections[0].expected_income == 0
    assert result.projections[0].expected_expenses == 0
    # Balance includes both cashbox starting balances
    current_balance = get_current_balance(db, test_budget.id)
    assert current_balance == 1000000 + 50000  # 1050000
    assert result.projections[0].end_balance == current_balance


def test_calculate_forecast_excludes_non_cashbox_only_posts(
    db: Session, test_budget: Budget, test_container: Container, test_user: User
):
    """Test that posts with only non-cashbox containers are excluded."""
    # Create a piggybank container
    sparegris = Container(
        budget_id=test_budget.id,
        name="Sparegris",
        type=ContainerType.PIGGYBANK,
        starting_balance=0,
        credit_limit=0,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(sparegris)
    db.flush()

    # Create income post bound ONLY to sparegris (should be excluded)
    sparegris_income = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Indtægt", "Renter"],
        display_order=[0, 0],
        direction=BudgetPostDirection.INCOME,
        accumulate=False,
        container_ids=[str(sparegris.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(sparegris_income)
    db.flush()

    today = date.today()
    sparegris_pattern = AmountPattern(
        budget_post_id=sparegris_income.id,
        amount=10000,  # 100 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        container_ids=[str(sparegris.id)],
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(sparegris_pattern)
    db.commit()

    result = calculate_forecast(db, test_budget.id, months=1)

    # Should not include sparegris-only income
    assert result.projections[0].expected_income == 0
    assert result.projections[0].expected_expenses == 0
    assert result.projections[0].end_balance == 1000000
