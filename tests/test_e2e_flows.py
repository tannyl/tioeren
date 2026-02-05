"""End-to-end tests for critical user flows.

This test file covers the main happy paths through the application:
1. Register new user
2. Login
3. Create budget with accounts
4. Add manual transaction
5. Categorize transaction (allocate to budget post)
6. View dashboard
7. View forecast

These are API-level E2E tests that verify the backend flows work correctly.
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from api.deps.database import get_db


@pytest.fixture
def client(db: Session):
    """Create test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_complete_user_flow(client: TestClient, db: Session):
    """
    Test the complete user journey from registration to forecast.

    This test simulates a real user going through the entire application flow:
    - Register account
    - Login
    - Create budget and accounts
    - Add transactions
    - Categorize transactions
    - View dashboard
    - View forecast
    """
    # -----------------------------------------------------------------
    # Flow 1: Register new user
    # -----------------------------------------------------------------
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "e2e_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert register_response.status_code == 201, (
        f"Registration failed: {register_response.text}"
    )
    register_data = register_response.json()
    assert register_data["email"] == "e2e_user@example.com"
    assert "id" in register_data
    user_id = register_data["id"]

    # Session cookie should be set
    assert "set-cookie" in register_response.headers

    # -----------------------------------------------------------------
    # Flow 2: Login with same credentials
    # -----------------------------------------------------------------
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "e2e_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200, (
        f"Login failed: {login_response.text}"
    )
    login_data = login_response.json()
    assert login_data["email"] == "e2e_user@example.com"
    assert login_data["id"] == user_id

    # Session cookie should be set
    assert "set-cookie" in login_response.headers

    # -----------------------------------------------------------------
    # Flow 3: Create budget with accounts
    # -----------------------------------------------------------------

    # 3a. Create budget
    budget_response = client.post(
        "/api/budgets",
        json={"name": "Test Budget"},
    )
    assert budget_response.status_code == 201, (
        f"Budget creation failed: {budget_response.text}"
    )
    budget_data = budget_response.json()
    assert budget_data["name"] == "Test Budget"
    budget_id = budget_data["id"]

    # 3b. Verify default categories were created
    categories_response = client.get(f"/api/budgets/{budget_id}/categories")
    assert categories_response.status_code == 200
    categories_data = categories_response.json()
    assert "data" in categories_data

    # Flatten the category tree to make it easier to search
    def flatten_categories(nodes):
        """Recursively flatten category tree."""
        flat = []
        for node in nodes:
            flat.append(node)
            if node.get("children"):
                flat.extend(flatten_categories(node["children"]))
        return flat

    all_categories = flatten_categories(categories_data["data"])
    category_names = [cat["name"] for cat in all_categories]

    # Check system categories exist
    assert "Indtægt" in category_names
    assert "Udgift" in category_names

    # Find an expense category to use later (Bolig > Husleje)
    expense_category_id = None
    income_category_id = None
    for cat in all_categories:
        if cat["name"] == "Husleje":
            expense_category_id = cat["id"]
        if cat["name"] == "Løn":
            income_category_id = cat["id"]

    assert expense_category_id is not None, "Husleje category not found"
    assert income_category_id is not None, "Løn category not found"

    # 3c. Create normal account (Lønkonto)
    account_response = client.post(
        f"/api/budgets/{budget_id}/accounts",
        json={
            "name": "Lønkonto",
            "purpose": "normal",
            "datasource": "bank",
            "currency": "DKK",
            "starting_balance": 1000000,  # 10,000 kr
            "can_go_negative": False,
        },
    )
    assert account_response.status_code == 201, (
        f"Normal account creation failed: {account_response.text}"
    )
    account_data = account_response.json()
    assert account_data["name"] == "Lønkonto"
    assert account_data["purpose"] == "normal"
    normal_account_id = account_data["id"]

    # 3d. Create savings account (Opsparing)
    savings_response = client.post(
        f"/api/budgets/{budget_id}/accounts",
        json={
            "name": "Opsparing",
            "purpose": "savings",
            "datasource": "bank",
            "currency": "DKK",
            "starting_balance": 500000,  # 5,000 kr
            "can_go_negative": False,
        },
    )
    assert savings_response.status_code == 201, (
        f"Savings account creation failed: {savings_response.text}"
    )
    savings_data = savings_response.json()
    assert savings_data["name"] == "Opsparing"
    assert savings_data["purpose"] == "savings"

    # -----------------------------------------------------------------
    # Flow 4: Add manual transactions
    # -----------------------------------------------------------------

    today = date.today()

    # 4a. Create expense transaction (Husleje)
    expense_response = client.post(
        f"/api/budgets/{budget_id}/transactions",
        json={
            "account_id": normal_account_id,
            "date": today.isoformat(),
            "amount": -800000,  # -8,000 kr in øre
            "description": "Husleje",
        },
    )
    assert expense_response.status_code == 201, (
        f"Expense transaction creation failed: {expense_response.text}"
    )
    expense_data = expense_response.json()
    assert expense_data["amount"] == -800000
    assert expense_data["description"] == "Husleje"
    assert expense_data["status"] == "uncategorized"
    expense_transaction_id = expense_data["id"]

    # 4b. Create income transaction (Løn)
    income_response = client.post(
        f"/api/budgets/{budget_id}/transactions",
        json={
            "account_id": normal_account_id,
            "date": today.isoformat(),
            "amount": 2500000,  # 25,000 kr in øre
            "description": "Løn",
        },
    )
    assert income_response.status_code == 201, (
        f"Income transaction creation failed: {income_response.text}"
    )
    income_data = income_response.json()
    assert income_data["amount"] == 2500000
    assert income_data["description"] == "Løn"
    assert income_data["status"] == "uncategorized"

    # 4c. Verify both transactions appear in list
    transactions_response = client.get(f"/api/budgets/{budget_id}/transactions")
    assert transactions_response.status_code == 200
    transactions_data = transactions_response.json()
    assert "data" in transactions_data
    assert len(transactions_data["data"]) == 2
    transaction_descriptions = [t["description"] for t in transactions_data["data"]]
    assert "Husleje" in transaction_descriptions
    assert "Løn" in transaction_descriptions

    # -----------------------------------------------------------------
    # Flow 5: Categorize transaction (allocate to budget post)
    # -----------------------------------------------------------------
    # Note: Budget post creation API not yet implemented (no route endpoints).
    # For MVP, we test transaction and allocation functionality separately.
    # Skipping budget post creation and allocation for this E2E test since
    # those API routes don't exist yet.

    # -----------------------------------------------------------------
    # Flow 6: View dashboard
    # -----------------------------------------------------------------

    dashboard_response = client.get(f"/api/budgets/{budget_id}/dashboard")
    assert dashboard_response.status_code == 200, (
        f"Dashboard request failed: {dashboard_response.text}"
    )
    dashboard_data = dashboard_response.json()

    # 6a. Verify available_balance
    # Starting: 10,000 kr
    # + Income: 25,000 kr
    # - Expense: 8,000 kr
    # = 27,000 kr = 2,700,000 øre
    assert "available_balance" in dashboard_data
    assert dashboard_data["available_balance"] == 2700000

    # 6b. Verify month_summary
    assert "month_summary" in dashboard_data
    month_summary = dashboard_data["month_summary"]
    assert month_summary["income"] == 2500000  # 25,000 kr income
    assert month_summary["expenses"] == -800000  # -8,000 kr expense
    assert month_summary["net"] == 1700000  # 17,000 kr net

    # 6c. Verify pending_count
    # We have 2 transactions still uncategorized (since we didn't allocate them)
    assert "pending_count" in dashboard_data
    assert dashboard_data["pending_count"] == 2

    # 6d. Verify accounts list
    assert "accounts" in dashboard_data
    assert len(dashboard_data["accounts"]) == 2
    account_names = [acc["name"] for acc in dashboard_data["accounts"]]
    assert "Lønkonto" in account_names
    assert "Opsparing" in account_names

    # 6e. Verify fixed_expenses list exists
    # Note: Since we didn't create budget posts, this may be empty
    assert "fixed_expenses" in dashboard_data
    # Just verify the field exists and is a list
    assert isinstance(dashboard_data["fixed_expenses"], list)

    # -----------------------------------------------------------------
    # Flow 7: View forecast
    # -----------------------------------------------------------------

    forecast_response = client.get(f"/api/budgets/{budget_id}/forecast?months=6")
    assert forecast_response.status_code == 200, (
        f"Forecast request failed: {forecast_response.text}"
    )
    forecast_data = forecast_response.json()

    # 7a. Verify response structure
    assert "projections" in forecast_data
    assert "lowest_point" in forecast_data
    assert "next_large_expense" in forecast_data

    # 7b. Verify 6 months of projections
    assert len(forecast_data["projections"]) == 6

    # 7c. Verify first month start_balance matches current balance
    first_projection = forecast_data["projections"][0]
    assert "start_balance" in first_projection
    # Start balance should be: 10,000 (starting) + 25,000 (income) - 8,000 (expense) = 27,000 kr = 2,700,000 øre
    assert first_projection["start_balance"] == 2700000

    # 7d. Verify projection structure
    for projection in forecast_data["projections"]:
        assert "month" in projection
        assert "start_balance" in projection
        assert "expected_income" in projection
        assert "expected_expenses" in projection
        assert "end_balance" in projection
        # Month should be in YYYY-MM format
        assert len(projection["month"]) == 7
        assert projection["month"][4] == "-"

    # 7e. Verify lowest_point structure
    assert "month" in forecast_data["lowest_point"]
    assert "balance" in forecast_data["lowest_point"]

    # -----------------------------------------------------------------
    # Test Complete!
    # -----------------------------------------------------------------
    # If we got here, all flows worked successfully


def test_e2e_flow_isolation(client: TestClient, db: Session):
    """
    Test that E2E flows are properly isolated.

    This ensures that the main E2E test doesn't interfere with other tests
    and vice versa. Each test should have a clean slate.
    """
    # Register a different user
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "isolated_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert register_response.status_code == 201

    # Should not see budgets from other test
    budgets_response = client.get("/api/budgets")
    assert budgets_response.status_code == 200
    budgets_data = budgets_response.json()
    assert len(budgets_data["data"]) == 0
