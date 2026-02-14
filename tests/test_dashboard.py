"""Tests for dashboard endpoint."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.transaction import Transaction, TransactionStatus
from api.models.category import Category
from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection, CounterpartyType
from api.models.amount_pattern import AmountPattern
from api.models.transaction_allocation import TransactionAllocation


@pytest.fixture
def db_session(db: Session):
    """Alias for db fixture to match test signatures."""
    return db


def test_get_dashboard_basic(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    test_user: User,
) -> None:
    """Test getting dashboard with basic data."""
    # Create budget
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
        warning_threshold=100000,
    )
    db_session.add(budget)
    db_session.flush()

    # Create accounts
    account1 = Account(
        budget_id=budget.id,
        name="Checking",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        starting_balance=1000000,  # 10,000 kr
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    account2 = Account(
        budget_id=budget.id,
        name="Credit Card",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.CREDIT,
        starting_balance=-50000,  # -500 kr
        can_go_negative=True,
        needs_coverage=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add_all([account1, account2])
    db_session.flush()

    # Add transactions to account1
    today = date.today()
    trans1 = Transaction(
        account_id=account1.id,
        date=today,
        amount=50000,  # +500 kr income
        description="Test income",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    trans2 = Transaction(
        account_id=account1.id,
        date=today,
        amount=-20000,  # -200 kr expense
        description="Test expense",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    trans3 = Transaction(
        account_id=account1.id,
        date=today,
        amount=-10000,  # -100 kr expense
        description="Uncategorized",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
    )
    db_session.add_all([trans1, trans2, trans3])
    db_session.commit()

    # Get dashboard
    response = client.get(
        f"/api/budgets/{budget.id}/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "available_balance" in data
    assert "accounts" in data
    assert "month_summary" in data
    assert "pending_count" in data
    assert "fixed_expenses" in data

    # Check available balance (normal accounts only)
    # account1: 1000000 + 50000 - 20000 - 10000 = 1020000
    # account2: -50000
    # Total: 1020000 + (-50000) = 970000
    assert data["available_balance"] == 970000

    # Check accounts
    assert len(data["accounts"]) == 2
    account_ids = {acc["id"] for acc in data["accounts"]}
    assert str(account1.id) in account_ids
    assert str(account2.id) in account_ids

    # Find checking account
    checking = next(acc for acc in data["accounts"] if acc["name"] == "Checking")
    assert checking["balance"] == 1020000  # 1000000 + 50000 - 20000 - 10000
    assert checking["purpose"] == "normal"

    # Check month summary
    assert data["month_summary"]["income"] == 50000
    assert data["month_summary"]["expenses"] == -30000  # -20000 + -10000
    assert data["month_summary"]["net"] == 20000

    # Check pending count
    assert data["pending_count"] == 1

    # Check fixed expenses (should be empty - no fixed budget posts)
    assert data["fixed_expenses"] == []


def test_get_dashboard_with_fixed_expenses(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    test_user: User,
) -> None:
    """Test dashboard with fixed budget posts."""
    # Create budget
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
        warning_threshold=100000,
    )
    db_session.add(budget)
    db_session.flush()

    # Create account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        starting_balance=1000000,
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(account)
    db_session.flush()

    # Create expense categories (one per budget post, as per new model)
    category_rent = Category(
        budget_id=budget.id,
        name="Rent",
        parent_id=None,
        is_system=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    category_insurance = Category(
        budget_id=budget.id,
        name="Insurance",
        parent_id=None,
        is_system=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add_all([category_rent, category_insurance])
    db_session.flush()

    # Create fixed budget posts
    bp_paid = BudgetPost(
        budget_id=budget.id,
        category_id=category_rent.id,
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    bp_pending = BudgetPost(
        budget_id=budget.id,
        category_id=category_insurance.id,
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add_all([bp_paid, bp_pending])
    db_session.flush()

    # Create amount patterns for the budget posts
    today = date.today()
    amount_pattern_paid = AmountPattern(
        budget_post_id=bp_paid.id,
        amount=-800000,  # -8000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    amount_pattern_pending = AmountPattern(
        budget_post_id=bp_pending.id,
        amount=-120000,  # -1200 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add_all([amount_pattern_paid, amount_pattern_pending])
    db_session.flush()

    # Create transaction allocated to the paid budget post
    today = date.today()
    trans = Transaction(
        account_id=account.id,
        date=today,
        amount=-800000,
        description="Rent payment",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
    )
    db_session.add(trans)
    db_session.flush()

    # Create allocation
    allocation = TransactionAllocation(
        transaction_id=trans.id,
        amount_pattern_id=amount_pattern_paid.id,
        amount=-800000,
        is_remainder=True,
    )
    db_session.add(allocation)
    db_session.commit()

    # Get dashboard
    response = client.get(
        f"/api/budgets/{budget.id}/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check fixed expenses
    assert len(data["fixed_expenses"]) == 2

    # Find rent (should be paid)
    rent = next(exp for exp in data["fixed_expenses"] if exp["name"] == "Rent")
    assert rent["expected_amount"] == -800000
    assert rent["status"] == "paid"
    assert rent["actual_amount"] == -800000

    # Find insurance (should be pending or overdue depending on date)
    insurance = next(exp for exp in data["fixed_expenses"] if exp["name"] == "Insurance")
    assert insurance["expected_amount"] == -120000
    assert insurance["status"] in ["pending", "overdue"]
    assert insurance["actual_amount"] is None


def test_get_dashboard_unauthorized(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    test_user: User,
) -> None:
    """Test getting dashboard for budget owned by another user."""
    # Create another user and their budget
    other_user = User(
        email="inlinedashboardother@example.com",
        password_hash="dummy_hash",
        email_verified=True,
    )
    db_session.add(other_user)
    db_session.flush()

    budget = Budget(
        name="Other Budget",
        owner_id=other_user.id,
        warning_threshold=100000,
    )
    db_session.add(budget)
    db_session.commit()

    # Try to access dashboard
    response = client.get(
        f"/api/budgets/{budget.id}/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 404  # Not found (user doesn't have access)


def test_get_dashboard_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting dashboard for non-existent budget."""
    fake_id = uuid.uuid4()

    response = client.get(
        f"/api/budgets/{fake_id}/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_dashboard_invalid_uuid(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting dashboard with invalid UUID."""
    response = client.get(
        "/api/budgets/not-a-uuid/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_dashboard_multiple_accounts(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    test_user: User,
) -> None:
    """Test dashboard with multiple account purposes."""
    # Create budget
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
        warning_threshold=100000,
    )
    db_session.add(budget)
    db_session.flush()

    # Create accounts with different purposes
    normal_account = Account(
        budget_id=budget.id,
        name="Checking",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        starting_balance=1000000,
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    savings_account = Account(
        budget_id=budget.id,
        name="Savings",
        purpose=AccountPurpose.SAVINGS,
        datasource=AccountDatasource.BANK,
        starting_balance=5000000,  # 50,000 kr
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    loan_account = Account(
        budget_id=budget.id,
        name="Car Loan",
        purpose=AccountPurpose.LOAN,
        datasource=AccountDatasource.VIRTUAL,
        starting_balance=-15000000,  # -150,000 kr debt
        can_go_negative=True,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add_all([normal_account, savings_account, loan_account])
    db_session.commit()

    # Get dashboard
    response = client.get(
        f"/api/budgets/{budget.id}/dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check available balance (only normal accounts)
    assert data["available_balance"] == 1000000

    # Check all accounts are present
    assert len(data["accounts"]) == 3
    account_names = {acc["name"] for acc in data["accounts"]}
    assert "Checking" in account_names
    assert "Savings" in account_names
    assert "Car Loan" in account_names

    # Verify balances
    checking = next(acc for acc in data["accounts"] if acc["name"] == "Checking")
    assert checking["balance"] == 1000000

    savings = next(acc for acc in data["accounts"] if acc["name"] == "Savings")
    assert savings["balance"] == 5000000

    loan = next(acc for acc in data["accounts"] if acc["name"] == "Car Loan")
    assert loan["balance"] == -15000000
