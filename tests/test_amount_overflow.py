"""Tests for amount field overflow validation (BUG-022)."""

import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.category import Category


# PostgreSQL BIGINT max value
MAX_BIGINT = 9_223_372_036_854_775_807


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
def test_account(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a test account."""
    account = Account(
        budget_id=test_budget.id,
        name="Test Account",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=1000000,
        can_go_negative=True,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_category(db: Session, test_budget: Budget, test_user: User) -> Category:
    """Create a test category."""
    category = Category(
        budget_id=test_budget.id,
        name="Test Category",
        is_system=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


class TestTransactionAmountOverflow:
    """Test transaction amount field bounds."""

    def test_create_transaction_amount_exceeds_max(
        self, client: TestClient, test_budget: Budget, test_account: Account, auth_headers: dict[str, str]
    ):
        """Amount exceeding MAX_BIGINT returns 422 validation error."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "account_id": str(test_account.id),
                "date": date.today().isoformat(),
                "amount": MAX_BIGINT + 1,  # Overflow
                "description": "Overflow test",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        # Verify it's a validation error, not 500 internal server error
        data = response.json()
        assert "detail" in data
        # Should not contain traceback
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "psycopg" not in response_text

    def test_create_transaction_amount_below_min(
        self, client: TestClient, test_budget: Budget, test_account: Account, auth_headers: dict[str, str]
    ):
        """Amount below -MAX_BIGINT returns 422 validation error."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "account_id": str(test_account.id),
                "date": date.today().isoformat(),
                "amount": -MAX_BIGINT - 1,  # Underflow
                "description": "Underflow test",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        response_text = response.text.lower()
        assert "traceback" not in response_text

    def test_create_transaction_amount_at_max(
        self, client: TestClient, test_budget: Budget, test_account: Account, auth_headers: dict[str, str]
    ):
        """Amount at MAX_BIGINT is accepted."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "account_id": str(test_account.id),
                "date": date.today().isoformat(),
                "amount": MAX_BIGINT,  # At boundary
                "description": "Max boundary test",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == MAX_BIGINT

    def test_update_transaction_amount_exceeds_max(
        self, client: TestClient, db: Session, test_budget: Budget, test_account: Account, test_user: User, auth_headers: dict[str, str]
    ):
        """Updating to amount exceeding MAX_BIGINT returns 422."""
        from api.models.transaction import Transaction, TransactionStatus

        transaction = Transaction(
            account_id=test_account.id,
            date=date.today(),
            amount=1000,
            description="Original",
            status=TransactionStatus.UNCATEGORIZED,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(transaction)
        db.commit()

        response = client.put(
            f"/api/budgets/{test_budget.id}/transactions/{transaction.id}",
            json={"amount": MAX_BIGINT + 1},
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAccountAmountOverflow:
    """Test account starting_balance field bounds."""

    def test_create_account_starting_balance_exceeds_max(
        self, client: TestClient, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """starting_balance exceeding MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json={
                "name": "Overflow Account",
                "purpose": "normal",
                "datasource": "bank",
                "currency": "DKK",
                "starting_balance": MAX_BIGINT + 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        response_text = response.text.lower()
        assert "traceback" not in response_text

    def test_create_account_starting_balance_below_min(
        self, client: TestClient, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """starting_balance below -MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json={
                "name": "Underflow Account",
                "purpose": "normal",
                "datasource": "bank",
                "currency": "DKK",
                "starting_balance": -MAX_BIGINT - 1,
                "can_go_negative": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_update_account_starting_balance_exceeds_max(
        self, client: TestClient, test_account: Account, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """Updating to starting_balance exceeding MAX_BIGINT returns 422."""
        response = client.put(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}",
            json={"starting_balance": MAX_BIGINT + 1},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestBudgetAmountOverflow:
    """Test budget warning_threshold field bounds."""

    def test_create_budget_warning_threshold_exceeds_max(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        """warning_threshold exceeding MAX_BIGINT returns 422."""
        response = client.post(
            "/api/budgets",
            json={
                "name": "Overflow Budget",
                "warning_threshold": MAX_BIGINT + 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_update_budget_warning_threshold_exceeds_max(
        self, client: TestClient, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """Updating to warning_threshold exceeding MAX_BIGINT returns 422."""
        response = client.put(
            f"/api/budgets/{test_budget.id}",
            json={"warning_threshold": MAX_BIGINT + 1},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestBudgetPostAmountOverflow:
    """Test budget post amount pattern field bounds."""

    def test_create_budget_post_amount_exceeds_max(
        self, client: TestClient, test_budget: Budget, test_category: Category, auth_headers: dict[str, str]
    ):
        """Amount pattern amount exceeding MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/budget-posts",
            json={
                "direction": "expense",
                "category_id": str(test_category.id),
                "type": "fixed",
                "counterparty_type": "external",
                "amount_patterns": [
                    {
                        "amount": MAX_BIGINT + 1,
                        "start_date": "2026-01-01",
                        "recurrence_pattern": {
                            "type": "monthly_fixed",
                            "interval": 1,
                            "day_of_month": 1,
                        },
                    }
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        response_text = response.text.lower()
        assert "traceback" not in response_text



class TestAllocationAmountOverflow:
    """Test transaction allocation amount field bounds."""

    def test_allocate_transaction_amount_exceeds_max(
        self, client: TestClient, db: Session, test_budget: Budget, test_account: Account, test_category: Category, test_user: User, auth_headers: dict[str, str]
    ):
        """Allocation amount exceeding MAX_BIGINT returns 422."""
        from api.models.transaction import Transaction, TransactionStatus
        from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection, CounterpartyType
        from api.models.amount_pattern import AmountPattern
        from datetime import date

        # Create budget post with amount pattern
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            direction=BudgetPostDirection.EXPENSE,
            category_id=test_category.id,
            type=BudgetPostType.FIXED,
            accumulate=False,
            counterparty_type=CounterpartyType.EXTERNAL,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget_post)
        db.flush()

        amount_pattern = AmountPattern(
            budget_post_id=budget_post.id,
            amount=100000,
            start_date=date(2026, 1, 1),
            end_date=None,
            recurrence_pattern={"type": "once"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(amount_pattern)
        db.commit()
        db.refresh(amount_pattern)

        # Create transaction
        transaction = Transaction(
            account_id=test_account.id,
            date=date.today(),
            amount=-100000,
            description="Test transaction",
            status=TransactionStatus.UNCATEGORIZED,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(transaction)
        db.commit()

        # Try to allocate with overflow amount
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions/{transaction.id}/allocate",
            json={
                "allocations": [
                    {
                        "amount_pattern_id": str(amount_pattern.id),
                        "amount": MAX_BIGINT + 1,
                    }
                ]
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
