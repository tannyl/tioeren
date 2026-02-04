"""Tests for Account CRUD API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.main import app
from api.deps.database import get_db
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.budget import Budget
from api.models.user import User
from api.services.auth import hash_password


@pytest.fixture
def client(db: DBSession):
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


@pytest.fixture
def test_user(db: DBSession) -> User:
    """Create a test user."""
    user = User(
        email="accountuser@example.com",
        password_hash=hash_password("SecurePassword123!"),
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: DBSession) -> User:
    """Create another test user for authorization tests."""
    user = User(
        email="otheraccount@example.com",
        password_hash=hash_password("SecurePassword123!"),
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
def test_account(db: DBSession, test_budget: Budget, test_user: User) -> Account:
    """Create a test account."""
    account = Account(
        budget_id=test_budget.id,
        name="Test Account",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=100000,  # 1000.00 kr
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
def authenticated_client(client, test_user):
    """Create authenticated client."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 200
    return client


class TestListAccounts:
    """Tests for GET /api/budgets/{budget_id}/accounts"""

    def test_list_accounts_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test listing accounts for a budget."""
        # Create another account
        account2 = Account(
            budget_id=test_budget.id,
            name="Second Account",
            purpose=AccountPurpose.SAVINGS,
            datasource=AccountDatasource.BANK,
            currency="DKK",
            starting_balance=50000,
            can_go_negative=False,
            needs_coverage=False,
        )
        db.add(account2)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/accounts")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

        # Check that both accounts are present
        account_names = {acc["name"] for acc in data["data"]}
        assert account_names == {"Test Account", "Second Account"}

        # Check second account details
        second_account = next(acc for acc in data["data"] if acc["name"] == "Second Account")
        assert second_account["purpose"] == "savings"
        assert second_account["datasource"] == "bank"
        assert second_account["starting_balance"] == 50000
        assert second_account["current_balance"] == 50000

    def test_list_accounts_empty(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test listing accounts when budget has none."""
        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/accounts")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    def test_list_accounts_excludes_soft_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test that soft-deleted accounts are not listed."""
        from datetime import datetime, UTC

        test_account.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{test_budget.id}/accounts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0

    def test_list_accounts_other_user_budget(
        self,
        authenticated_client: TestClient,
        other_budget: Budget,
    ):
        """Test that user cannot list accounts from another user's budget."""
        response = authenticated_client.get(f"/api/budgets/{other_budget.id}/accounts")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_accounts_invalid_budget_id(
        self,
        authenticated_client: TestClient,
    ):
        """Test listing accounts with invalid budget ID."""
        response = authenticated_client.get("/api/budgets/invalid-uuid/accounts")

        assert response.status_code == 404


class TestCreateAccount:
    """Tests for POST /api/budgets/{budget_id}/accounts"""

    def test_create_account_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        db: DBSession,
    ):
        """Test creating an account successfully."""
        account_data = {
            "name": "New Account",
            "purpose": "normal",
            "datasource": "bank",
            "currency": "DKK",
            "starting_balance": 100000,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Account"
        assert data["purpose"] == "normal"
        assert data["datasource"] == "bank"
        assert data["starting_balance"] == 100000
        assert data["can_go_negative"] is False  # Default for bank
        assert data["needs_coverage"] is False  # Default for bank
        assert data["current_balance"] == 100000

        # Verify in database
        account = db.query(Account).filter(Account.id == uuid.UUID(data["id"])).first()
        assert account is not None
        assert account.name == "New Account"

    def test_create_account_credit_defaults(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating a credit account uses correct defaults."""
        account_data = {
            "name": "Credit Card",
            "purpose": "normal",
            "datasource": "credit",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["can_go_negative"] is True  # Default for credit
        assert data["needs_coverage"] is True  # Default for credit

    def test_create_account_override_defaults(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating account with explicit can_go_negative/needs_coverage."""
        account_data = {
            "name": "Virtual Account",
            "purpose": "normal",
            "datasource": "virtual",
            "starting_balance": 50000,
            "can_go_negative": True,
            "needs_coverage": False,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["can_go_negative"] is True
        assert data["needs_coverage"] is False

    def test_create_account_duplicate_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
    ):
        """Test creating account with duplicate name in same budget."""
        account_data = {
            "name": test_account.name,  # Same name
            "purpose": "normal",
            "datasource": "bank",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_account_different_budget_same_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test that same account name can exist in different budgets."""
        # Create account in test_budget with a name
        existing_name = "Shared Name"
        account1 = Account(
            budget_id=test_budget.id,
            name=existing_name,
            purpose=AccountPurpose.NORMAL,
            datasource=AccountDatasource.BANK,
            starting_balance=0,
        )
        db.add(account1)
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

        account_data = {
            "name": existing_name,  # Same name as in test_budget
            "purpose": "normal",
            "datasource": "bank",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{budget2.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 201  # Should succeed in different budget

    def test_create_account_invalid_budget(
        self,
        authenticated_client: TestClient,
    ):
        """Test creating account for non-existent budget."""
        account_data = {
            "name": "Test",
            "purpose": "normal",
            "datasource": "bank",
            "starting_balance": 0,
        }

        fake_budget_id = uuid.uuid4()
        response = authenticated_client.post(
            f"/api/budgets/{fake_budget_id}/accounts",
            json=account_data,
        )

        assert response.status_code == 404

    def test_create_account_other_user_budget(
        self,
        authenticated_client: TestClient,
        other_budget: Budget,
    ):
        """Test that user cannot create account in another user's budget."""
        account_data = {
            "name": "Unauthorized Account",
            "purpose": "normal",
            "datasource": "bank",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{other_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 404


class TestGetAccount:
    """Tests for GET /api/budgets/{budget_id}/accounts/{account_id}"""

    def test_get_account_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
    ):
        """Test getting a single account."""
        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_account.id)
        assert data["name"] == test_account.name
        assert data["purpose"] == test_account.purpose.value
        assert data["starting_balance"] == test_account.starting_balance

    def test_get_account_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test getting non-existent account."""
        fake_account_id = uuid.uuid4()
        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/accounts/{fake_account_id}"
        )

        assert response.status_code == 404

    def test_get_account_soft_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test that soft-deleted account returns 404."""
        from datetime import datetime, UTC

        test_account.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.get(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 404

    def test_get_account_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_account: Account,
    ):
        """Test getting account with wrong budget ID."""
        response = authenticated_client.get(
            f"/api/budgets/{other_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 404


class TestUpdateAccount:
    """Tests for PUT /api/budgets/{budget_id}/accounts/{account_id}"""

    def test_update_account_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test updating account name."""
        update_data = {"name": "Updated Account Name"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Account Name"

        # Verify in database
        db.refresh(test_account)
        assert test_account.name == "Updated Account Name"

    def test_update_account_multiple_fields(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test updating multiple fields at once."""
        update_data = {
            "name": "New Name",
            "starting_balance": 200000,
            "can_go_negative": True,
        }

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["starting_balance"] == 200000
        assert data["can_go_negative"] is True

    def test_update_account_duplicate_name(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test updating account to duplicate name."""
        # Create another account
        account2 = Account(
            budget_id=test_budget.id,
            name="Second Account",
            purpose=AccountPurpose.NORMAL,
            datasource=AccountDatasource.BANK,
            starting_balance=0,
        )
        db.add(account2)
        db.commit()

        # Try to rename test_account to account2's name
        update_data = {"name": "Second Account"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}",
            json=update_data,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_update_account_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test updating non-existent account."""
        fake_account_id = uuid.uuid4()
        update_data = {"name": "New Name"}

        response = authenticated_client.put(
            f"/api/budgets/{test_budget.id}/accounts/{fake_account_id}",
            json=update_data,
        )

        assert response.status_code == 404

    def test_update_account_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_account: Account,
    ):
        """Test updating account with wrong budget ID."""
        update_data = {"name": "New Name"}

        response = authenticated_client.put(
            f"/api/budgets/{other_budget.id}/accounts/{test_account.id}",
            json=update_data,
        )

        assert response.status_code == 404


class TestDeleteAccount:
    """Tests for DELETE /api/budgets/{budget_id}/accounts/{account_id}"""

    def test_delete_account_success(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test soft deleting an account."""
        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 204

        # Verify soft delete in database
        db.refresh(test_account)
        assert test_account.deleted_at is not None

    def test_delete_account_not_found(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test deleting non-existent account."""
        fake_account_id = uuid.uuid4()
        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/accounts/{fake_account_id}"
        )

        assert response.status_code == 404

    def test_delete_account_already_deleted(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        test_account: Account,
        db: DBSession,
    ):
        """Test deleting already soft-deleted account."""
        from datetime import datetime, UTC

        test_account.deleted_at = datetime.now(UTC)
        db.commit()

        response = authenticated_client.delete(
            f"/api/budgets/{test_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 404

    def test_delete_account_wrong_budget(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
        other_budget: Budget,
        test_account: Account,
    ):
        """Test deleting account with wrong budget ID."""
        response = authenticated_client.delete(
            f"/api/budgets/{other_budget.id}/accounts/{test_account.id}"
        )

        assert response.status_code == 404


class TestAccountValidation:
    """Tests for account validation logic."""

    def test_create_account_missing_required_fields(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating account without required fields."""
        account_data = {
            "name": "Test Account",
            # Missing purpose, datasource, starting_balance
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 422

    def test_create_account_invalid_enum_value(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating account with invalid enum value."""
        account_data = {
            "name": "Test Account",
            "purpose": "invalid_purpose",
            "datasource": "bank",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 422

    def test_create_account_name_too_long(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating account with name exceeding max length."""
        account_data = {
            "name": "A" * 256,  # Max is 255
            "purpose": "normal",
            "datasource": "bank",
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 422

    def test_create_account_currency_invalid_length(
        self,
        authenticated_client: TestClient,
        test_budget: Budget,
    ):
        """Test creating account with invalid currency code length."""
        account_data = {
            "name": "Test Account",
            "purpose": "normal",
            "datasource": "bank",
            "currency": "DKKK",  # Should be 3 chars
            "starting_balance": 0,
        }

        response = authenticated_client.post(
            f"/api/budgets/{test_budget.id}/accounts",
            json=account_data,
        )

        assert response.status_code == 422
