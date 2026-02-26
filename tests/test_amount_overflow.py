"""Tests for amount field overflow validation (BUG-022)."""

import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.container import Container, ContainerType


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
def test_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a test container."""
    container = Container(
        budget_id=test_budget.id,
        name="Test Container",
        type=ContainerType.CASHBOX,
        starting_balance=1000000,
        credit_limit=None,
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container



class TestTransactionAmountOverflow:
    """Test transaction amount field bounds."""

    def test_create_transaction_amount_exceeds_max(
        self, client: TestClient, test_budget: Budget, test_container: Account, auth_headers: dict[str, str]
    ):
        """Amount exceeding MAX_BIGINT returns 422 validation error."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "container_id": str(test_container.id),
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
        self, client: TestClient, test_budget: Budget, test_container: Account, auth_headers: dict[str, str]
    ):
        """Amount below -MAX_BIGINT returns 422 validation error."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "container_id": str(test_container.id),
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
        self, client: TestClient, test_budget: Budget, test_container: Account, auth_headers: dict[str, str]
    ):
        """Amount at MAX_BIGINT is accepted."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/transactions",
            json={
                "container_id": str(test_container.id),
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
        self, client: TestClient, db: Session, test_budget: Budget, test_container: Account, test_user: User, auth_headers: dict[str, str]
    ):
        """Updating to amount exceeding MAX_BIGINT returns 422."""
        from api.models.transaction import Transaction, TransactionStatus

        transaction = Transaction(
            container_id=test_container.id,
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


class TestContainerAmountOverflow:
    """Test container starting_balance field bounds."""

    def test_create_container_starting_balance_exceeds_max(
        self, client: TestClient, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """starting_balance exceeding MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json={
                "name": "Overflow Container",
                "type": "cashbox",
                "starting_balance": MAX_BIGINT + 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        response_text = response.text.lower()
        assert "traceback" not in response_text

    def test_create_container_starting_balance_below_min(
        self, client: TestClient, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """starting_balance below -MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json={
                "name": "Underflow Container",
                "type": "cashbox",
                "starting_balance": -MAX_BIGINT - 1,
                "credit_limit": None,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_update_container_starting_balance_exceeds_max(
        self, client: TestClient, test_container: Container, test_budget: Budget, auth_headers: dict[str, str]
    ):
        """Updating to starting_balance exceeding MAX_BIGINT returns 422."""
        response = client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
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
        self, client: TestClient, test_budget: Budget, test_container: Account, auth_headers: dict[str, str]
    ):
        """Amount pattern amount exceeding MAX_BIGINT returns 422."""
        response = client.post(
            f"/api/budgets/{test_budget.id}/budget-posts",
            json={
                "direction": "expense",
                "category_path": ["Udgift", "Test"],
                "display_order": [0, 0],
                "container_ids": [str(test_container.id)],
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
        self, client: TestClient, db: Session, test_budget: Budget, test_container: Account, test_user: User, auth_headers: dict[str, str]
    ):
        """Allocation amount exceeding MAX_BIGINT returns 422."""
        from api.models.transaction import Transaction, TransactionStatus
        from api.models.budget_post import BudgetPost, BudgetPostDirection
        from api.models.amount_pattern import AmountPattern
        from datetime import date
        from uuid import uuid4

        # Create budget post with amount pattern
        budget_post = BudgetPost(
            budget_id=test_budget.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Test", "Category"],
        display_order=[0, 0],
            accumulate=False,
            container_ids=[str(test_container.id)],  # Use test_container fixture
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
            container_id=test_container.id,
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
