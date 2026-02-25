"""Tests for Container CRUD API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.models.container import Container, ContainerType
from api.models.budget import Budget
from api.models.user import User


@pytest.fixture
def test_budget(db: DBSession, test_user: User) -> Budget:
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
def other_budget(db: DBSession, other_user: User) -> Budget:
    """Create a budget owned by other_user."""
    budget = Budget(
        name="Other Budget",
        owner_id=other_user.id,
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@pytest.fixture
def test_container(db: DBSession, test_budget: Budget, test_user: User) -> Container:
    """Create a test container."""
    container = Container(
        budget_id=test_budget.id,
        name="Test Container",
        type=ContainerType.CASHBOX,
        starting_balance=100000,  # 1000.00 kr
        locked=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


class TestListContainers:
    """Tests for GET /api/budgets/{budget_id}/containers"""

    def test_list_containers_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test listing containers for a budget."""
        # Create another container
        container2 = Container(
            budget_id=test_budget.id,
            name="Second Container",
            type=ContainerType.PIGGYBANK,
            starting_balance=50000,
            locked=False,
        )
        db.add(container2)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/containers")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

        # Check that both containers are present
        container_names = {cont["name"] for cont in data["data"]}
        assert container_names == {"Test Container", "Second Container"}

        # Check second container details
        second_container = next(cont for cont in data["data"] if cont["name"] == "Second Container")
        assert second_container["type"] == "piggybank"
        assert second_container["starting_balance"] == 50000
        assert second_container["current_balance"] == 50000

    def test_list_containers_empty(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test listing containers when budget has none."""
        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/containers")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    def test_list_containers_excludes_soft_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test that soft-deleted containers are not listed."""
        from datetime import datetime, UTC

        test_container.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/containers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0

    def test_list_containers_other_user_budget(
        self,
        authenticated_client: TestClient,
        other_budget: Budget,
    ):
        """Test that user cannot list containers from another user's budget."""
        response = authenticated_client.get(f"/api/budgets/{other_budget.id}/containers")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_containers_invalid_budget_id(
        self,
        authenticated_client: TestClient,
    ):
        """Test listing containers with invalid budget ID."""
        response = authenticated_client.get("/api/budgets/invalid-uuid/containers")

        assert response.status_code == 404


class TestCreateContainer:
    """Tests for POST /api/budgets/{budget_id}/containers"""

    def test_create_container_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        db: DBSession,
    ):
        """Test creating a container successfully."""
        container_data = {
            "name": "New Container",
            "type": "cashbox",
            "starting_balance": 100000,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Container"
        assert data["type"] == "cashbox"
        assert data["starting_balance"] == 100000
        assert data.get("overdraft_limit") is None
        # locked field may be None or False by default
        assert data["current_balance"] == 100000

        # Verify in database
        container = db.query(Container).filter(Container.id == uuid.UUID(data["id"])).first()
        assert container is not None
        assert container.name == "New Container"

    def test_create_container_with_overdraft_limit(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating a container with an overdraft limit."""
        container_data = {
            "name": "Kassekredit",
            "type": "cashbox",
            "starting_balance": 0,
            "overdraft_limit": -5000000,  # Can go to -50,000 kr (negative floor)
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["overdraft_limit"] == -5000000

    def test_create_container_locked_piggybank(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating a locked piggybank container."""
        container_data = {
            "name": "Locked Savings",
            "type": "piggybank",
            "starting_balance": 50000,
            "locked": True,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data.get("locked") is True
        assert data.get("overdraft_limit") is None

    def test_create_container_debt_with_credit_limit(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating a debt container with credit limit."""
        container_data = {
            "name": "Loan",
            "type": "debt",
            "starting_balance": -15000000,  # -150,000 kr
            "credit_limit": -20000000,  # Can go to -200,000 kr (negative floor)
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["credit_limit"] == -20000000
        assert data["starting_balance"] == -15000000

    def test_create_container_duplicate_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
    ):
        """Test creating container with duplicate name in same budget."""
        container_data = {
            "name": test_container.name,  # Same name
            "type": "cashbox",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_container_different_budget_same_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test that same container name can exist in different budgets."""
        # Create container in test_budget with a name
        existing_name = "Shared Name"
        container1 = Container(
            budget_id=test_budget.id,
            name=existing_name,
            type=ContainerType.CASHBOX,
            starting_balance=0,
        )
        db.add(container1)
        db.commit()

        # This should fail because we don't own other_budget
        # But shows that duplicate check is scoped to budget
        # Let's create a second budget for the same user instead
        budget2 = Budget(
            name="Second Budget",
            owner_id=test_budget.owner_id,
            created_by=test_budget.owner_id,
            updated_by=test_budget.owner_id,
        )
        db.add(budget2)
        db.commit()

        container_data = {
            "name": existing_name,  # Same name as in test_budget
            "type": "cashbox",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{budget2.id}/containers",
            json=container_data,
        )

        assert response.status_code == 201  # Should succeed in different budget

    def test_create_container_invalid_budget(
        self,
        authenticated_client: TestClient,
    ):
        """Test creating container for non-existent budget."""
        container_data = {
            "name": "Test",
            "type": "cashbox",
            "starting_balance": 0,
        }

        fake_budget_id = uuid.uuid4()
        response = authenticated_client.post(
            f"/api/budgets/{fake_budget_id}/containers",
            json=container_data,
        )

        assert response.status_code == 404

    def test_create_container_other_user_budget(
        self,
        authenticated_client: TestClient,
        other_budget: Budget,
    ):
        """Test that user cannot create container in another user's budget."""
        container_data = {
            "name": "Unauthorized Container",
            "type": "cashbox",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{other_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 404


class TestGetContainer:
    """Tests for GET /api/budgets/{budget_id}/containers/{container_id}"""

    def test_get_container_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
    ):
        """Test getting a single container."""
        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_container.id)
        assert data["name"] == test_container.name
        assert data["type"] == test_container.type.value
        assert data["starting_balance"] == test_container.starting_balance

    def test_get_container_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test getting non-existent container."""
        fake_container_id = uuid.uuid4()
        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/containers/{fake_container_id}"
        )

        assert response.status_code == 404

    def test_get_container_soft_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test that soft-deleted container returns 404."""
        from datetime import datetime, UTC

        test_container.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 404

    def test_get_container_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_container: Container,
    ):
        """Test getting container with wrong budget ID."""
        response = authenticated_client.get(
            f"/api/budgets/{other_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 404


class TestUpdateContainer:
    """Tests for PUT /api/budgets/{budget_id}/containers/{container_id}"""

    def test_update_container_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test updating container name."""
        update_data = {"name": "Updated Container Name"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Container Name"

        # Verify in database
        db.refresh(test_container)
        assert test_container.name == "Updated Container Name"

    def test_update_container_multiple_fields(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test updating multiple fields at once."""
        update_data = {
            "name": "New Name",
            "starting_balance": 200000,
            "overdraft_limit": -1000000,  # Can go to -10,000 kr (negative floor)
        }

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["starting_balance"] == 200000
        assert data["overdraft_limit"] == -1000000

    def test_update_container_duplicate_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test updating container to duplicate name."""
        # Create another container
        container2 = Container(
            budget_id=test_budget.id,
            name="Second Container",
            type=ContainerType.CASHBOX,
            starting_balance=0,
        )
        db.add(container2)
        db.commit()

        # Try to rename test_container to container2's name
        update_data = {"name": "Second Container"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_update_container_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test updating non-existent container."""
        fake_container_id = uuid.uuid4()
        update_data = {"name": "New Name"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{fake_container_id}",
            json=update_data,
        )

        assert response.status_code == 404

    def test_update_container_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_container: Container,
    ):
        """Test updating container with wrong budget ID."""
        update_data = {"name": "New Name"}

        response = authenticated_client.put(
            f"/api/budgets/{other_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 404


class TestDeleteContainer:
    """Tests for DELETE /api/budgets/{budget_id}/containers/{container_id}"""

    def test_delete_container_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test soft deleting a container."""
        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 204

        # Verify soft delete in database
        db.refresh(test_container)
        assert test_container.deleted_at is not None

    def test_delete_container_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test deleting non-existent container."""
        fake_container_id = uuid.uuid4()
        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/containers/{fake_container_id}"
        )

        assert response.status_code == 404

    def test_delete_container_already_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
        db: DBSession,
    ):
        """Test deleting already soft-deleted container."""
        from datetime import datetime, UTC

        test_container.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 404

    def test_delete_container_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_container: Container,
    ):
        """Test deleting container with wrong budget ID."""
        response = authenticated_client.delete(
            f"/api/budgets/{other_budget.id}/containers/{test_container.id}"
        )

        assert response.status_code == 404


class TestContainerValidation:
    """Tests for container validation logic."""

    def test_create_container_missing_required_fields(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating container without required fields."""
        container_data = {
            "name": "Test Container",
            # Missing type, starting_balance
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 422

    def test_create_container_invalid_enum_value(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating container with invalid enum value."""
        container_data = {
            "name": "Test Container",
            "type": "invalid_type",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 422

    def test_create_container_name_too_long(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating container with name exceeding max length."""
        container_data = {
            "name": "A" * 256,  # Max is 255
            "type": "cashbox",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 422

    def test_create_container_positive_credit_limit_rejected(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test that positive credit_limit is rejected (must be negative or zero)."""
        container_data = {
            "name": "Test Container",
            "type": "debt",
            "starting_balance": 0,
            "credit_limit": 5000,  # Positive value should be rejected
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 422

    def test_update_container_positive_credit_limit_rejected(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
    ):
        """Test that updating to positive credit_limit is rejected."""
        update_data = {
            "credit_limit": 10000,  # Positive value should be rejected
        }

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 422

    def test_create_container_positive_overdraft_limit_rejected(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test that positive overdraft_limit is rejected (must be negative or zero)."""
        container_data = {
            "name": "Test Container",
            "type": "cashbox",
            "starting_balance": 0,
            "overdraft_limit": 5000,  # Positive value should be rejected
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/containers",
            json=container_data,
        )

        assert response.status_code == 422

    def test_update_container_positive_overdraft_limit_rejected(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_container: Container,
    ):
        """Test that updating to positive overdraft_limit is rejected."""
        update_data = {
            "overdraft_limit": 10000,  # Positive value should be rejected
        }

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/containers/{test_container.id}",
            json=update_data,
        )

        assert response.status_code == 422
