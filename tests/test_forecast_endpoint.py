"""Tests for forecast endpoint."""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.container import Container, ContainerType
from api.models.budget_post import BudgetPost, BudgetPostDirection
from api.models.amount_pattern import AmountPattern
from api.models.transaction import Transaction


@pytest.fixture
def test_budget(db: Session, test_user: User) -> Budget:
    """Create a test budget."""
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@pytest.fixture
def test_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a test container with starting balance."""
    container = Container(
        budget_id=test_budget.id,
        name="Test Container",
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




@pytest.fixture
def test_budget_posts(
    db: Session, test_budget: Budget, test_container: Account, test_user: User
) -> list[BudgetPost]:
    """Create test budget posts with various recurrence patterns."""
    # Monthly income (salary)
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
    # Monthly expense (rent)
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
    # Quarterly expense (insurance)
    insurance = BudgetPost(
        budget_id=test_budget.id,
        category_path=["Udgift", "Forsikring"],
        display_order=[0, 1],
        direction=BudgetPostDirection.EXPENSE,
        accumulate=False,
        container_ids=[str(test_container.id)],  # Replaced counterparty
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    posts = [salary, rent, insurance]
    for post in posts:
        db.add(post)
    db.flush()

    # Create amount patterns - amounts are positive in new model
    today = date.today()
    salary_pattern = AmountPattern(
        budget_post_id=salary.id,
        amount=2500000,  # 25,000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 28, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    rent_pattern = AmountPattern(
        budget_post_id=rent.id,
        amount=800000,  # 8,000 kr (positive)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    insurance_pattern = AmountPattern(
        budget_post_id=insurance.id,
        amount=480000,  # 4,800 kr (positive, large expense for testing)
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 15, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([salary_pattern, rent_pattern, insurance_pattern])
    db.commit()
    for post in posts:
        db.refresh(post)
    return posts


@pytest.fixture
def test_transaction(db: Session, test_container: Account, test_user: User) -> Transaction:
    """Create a test transaction to adjust balance."""
    transaction = Transaction(
        container_id=test_container.id,
        date=date.today(),
        amount=-30000,  # -300 kr
        description="Test expense",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def test_get_forecast_default_months(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with default 12 months."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "projections" in data
    assert "lowest_point" in data
    assert "next_large_expense" in data

    # Verify 12 months of projections
    assert len(data["projections"]) == 12

    # Verify each projection has required fields
    for projection in data["projections"]:
        assert "month" in projection
        assert "start_balance" in projection
        assert "expected_income" in projection
        assert "expected_expenses" in projection
        assert "end_balance" in projection
        # Month should be in YYYY-MM format
        assert len(projection["month"]) == 7
        assert projection["month"][4] == "-"

    # Verify lowest point structure
    assert "month" in data["lowest_point"]
    assert "balance" in data["lowest_point"]

    # Verify next large expense (should exist with quarterly insurance)
    assert data["next_large_expense"] is not None
    assert "name" in data["next_large_expense"]
    assert "amount" in data["next_large_expense"]
    assert "date" in data["next_large_expense"]


def test_get_forecast_custom_months(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with custom number of months."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=6",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify 6 months of projections
    assert len(data["projections"]) == 6


def test_get_forecast_min_months(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with minimum months (1)."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["projections"]) == 1


def test_get_forecast_max_months(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with maximum months (24)."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=24",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["projections"]) == 24


def test_get_forecast_months_below_minimum(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with months below minimum (validation error)."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=0",
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


def test_get_forecast_months_above_maximum(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], auth_headers: dict[str, str]
):
    """Test getting forecast with months above maximum (validation error)."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=25",
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


def test_get_forecast_includes_transactions(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], test_transaction: Transaction, auth_headers: dict[str, str]
):
    """Test that forecast includes existing transactions in current balance."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # First projection should start with current balance
    # starting_balance (1000000) + transaction (-30000) = 970000
    first_projection = data["projections"][0]
    assert first_projection["start_balance"] == 970000


def test_get_forecast_unauthorized_user(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], other_auth_headers: dict[str, str]
):
    """Test that other users cannot access budget forecast."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast",
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert "Budget not found" in response.json()["detail"]


def test_get_forecast_unauthenticated(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost]
):
    """Test that unauthenticated requests are rejected."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast",
    )

    assert response.status_code == 401


def test_get_forecast_budget_not_found(
    client: TestClient, auth_headers: dict[str, str]
):
    """Test getting forecast for non-existent budget."""
    import uuid

    fake_budget_id = str(uuid.uuid4())

    response = client.get(
        f"/api/budgets/{fake_budget_id}/forecast",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "Budget not found" in response.json()["detail"]


def test_get_forecast_invalid_budget_uuid(
    client: TestClient, auth_headers: dict[str, str]
):
    """Test getting forecast with invalid budget UUID."""
    response = client.get(
        "/api/budgets/not-a-uuid/forecast",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "Budget not found" in response.json()["detail"]


def test_get_forecast_calculates_correctly(
    client: TestClient, test_budget: Budget, test_container: Account, test_budget_posts: list[BudgetPost], test_transaction: Transaction, auth_headers: dict[str, str]
):
    """Test that forecast calculations are correct."""
    response = client.get(
        f"/api/budgets/{test_budget.id}/forecast?months=3",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Current balance: 1000000 (starting) - 30000 (transaction) = 970000
    assert data["projections"][0]["start_balance"] == 970000

    # Each month should have income and expenses based on budget posts
    for projection in data["projections"]:
        # Income should be positive
        assert projection["expected_income"] >= 0
        # Expenses should be negative or zero
        assert projection["expected_expenses"] <= 0
        # End balance should equal start + income + expenses
        assert projection["end_balance"] == projection["start_balance"] + projection["expected_income"] + projection["expected_expenses"]

    # Next projection should start where previous ended
    for i in range(1, len(data["projections"])):
        assert data["projections"][i]["start_balance"] == data["projections"][i - 1]["end_balance"]
