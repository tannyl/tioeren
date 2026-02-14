"""Test transaction endpoints."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.transaction import Transaction, TransactionStatus


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
def second_account(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a second test account for transfers."""
    account = Account(
        budget_id=test_budget.id,
        name="Second Account",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=500000,  # 5,000 kr
        can_go_negative=False,
        needs_coverage=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_create_transaction(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    auth_headers: dict[str, str],
):
    """Test creating a transaction."""
    today = date.today()
    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions",
        json={
            "account_id": str(test_account.id),
            "date": today.isoformat(),
            "amount": -50000,  # -500 kr
            "description": "Test purchase",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == str(test_account.id)
    assert data["date"] == today.isoformat()
    assert data["amount"] == -50000
    assert data["description"] == "Test purchase"
    assert data["status"] == "uncategorized"
    assert data["is_internal_transfer"] is False
    assert data["counterpart_transaction_id"] is None

    # Verify in database
    transaction = db.query(Transaction).filter(
        Transaction.id == uuid.UUID(data["id"])
    ).first()
    assert transaction is not None
    assert transaction.amount == -50000


def test_create_internal_transfer(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    second_account: Account,
    auth_headers: dict[str, str],
):
    """Test creating an internal transfer between two accounts."""
    today = date.today()
    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions",
        json={
            "account_id": str(test_account.id),
            "date": today.isoformat(),
            "amount": -100000,  # -1,000 kr (outgoing)
            "description": "Transfer to Second Account",
            "is_internal_transfer": True,
            "counterpart_account_id": str(second_account.id),
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_internal_transfer"] is True
    assert data["status"] == "categorized"  # Internal transfers are auto-categorized
    assert data["counterpart_transaction_id"] is not None

    # Verify both transactions exist
    transaction1 = db.query(Transaction).filter(
        Transaction.id == uuid.UUID(data["id"])
    ).first()
    assert transaction1 is not None
    assert transaction1.amount == -100000
    assert transaction1.account_id == test_account.id

    transaction2 = db.query(Transaction).filter(
        Transaction.id == transaction1.counterpart_transaction_id
    ).first()
    assert transaction2 is not None
    assert transaction2.amount == 100000  # Positive (incoming)
    assert transaction2.account_id == second_account.id
    assert transaction2.counterpart_transaction_id == transaction1.id


def test_list_transactions(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test listing transactions."""
    # Create some test transactions
    today = date.today()
    for i in range(3):
        transaction = Transaction(
            account_id=test_account.id,
            date=today - timedelta(days=i),
            amount=-10000 * (i + 1),
            description=f"Transaction {i}",
            status=TransactionStatus.UNCATEGORIZED,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(transaction)
    db.commit()

    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "next_cursor" in data
    assert len(data["data"]) == 3
    # Should be sorted by date DESC
    assert data["data"][0]["description"] == "Transaction 0"
    assert data["data"][1]["description"] == "Transaction 1"
    assert data["data"][2]["description"] == "Transaction 2"


def test_list_transactions_with_account_filter(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    second_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test listing transactions filtered by account."""
    today = date.today()

    # Create transactions on first account
    for i in range(2):
        transaction = Transaction(
            account_id=test_account.id,
            date=today,
            amount=-10000,
            description=f"Account 1 Transaction {i}",
            status=TransactionStatus.UNCATEGORIZED,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(transaction)

    # Create transaction on second account
    transaction = Transaction(
        account_id=second_account.id,
        date=today,
        amount=-5000,
        description="Account 2 Transaction",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()

    # Filter by first account
    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions?account_id={test_account.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert all(t["account_id"] == str(test_account.id) for t in data["data"])


def test_list_transactions_with_status_filter(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test listing transactions filtered by status."""
    today = date.today()

    # Create uncategorized transaction
    transaction1 = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-10000,
        description="Uncategorized",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction1)

    # Create categorized transaction
    transaction2 = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-5000,
        description="Categorized",
        status=TransactionStatus.CATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction2)
    db.commit()

    # Filter by uncategorized status
    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions?status=uncategorized",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["status"] == "uncategorized"
    assert data["data"][0]["description"] == "Uncategorized"


def test_list_transactions_with_date_filter(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test listing transactions filtered by date range."""
    today = date.today()

    # Create transactions on different dates
    transaction1 = Transaction(
        account_id=test_account.id,
        date=today - timedelta(days=10),
        amount=-10000,
        description="Old transaction",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction1)

    transaction2 = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-5000,
        description="Recent transaction",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction2)
    db.commit()

    # Filter by date range (last 5 days)
    date_from = (today - timedelta(days=5)).isoformat()
    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions?date_from={date_from}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["description"] == "Recent transaction"


def test_get_transaction(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test getting a single transaction."""
    today = date.today()
    transaction = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-25000,
        description="Test transaction",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions/{transaction.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(transaction.id)
    assert data["amount"] == -25000
    assert data["description"] == "Test transaction"


def test_update_transaction(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test updating a transaction."""
    today = date.today()
    transaction = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-10000,
        description="Original description",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    response = client.put(
        f"/api/budgets/{test_budget.id}/transactions/{transaction.id}",
        json={
            "description": "Updated description",
            "amount": -15000,
            "status": "categorized",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["amount"] == -15000
    assert data["status"] == "categorized"

    # Verify in database
    db.refresh(transaction)
    assert transaction.description == "Updated description"
    assert transaction.amount == -15000
    assert transaction.status == TransactionStatus.CATEGORIZED


def test_delete_transaction(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test deleting a transaction."""
    today = date.today()
    transaction = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-10000,
        description="To be deleted",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()
    transaction_id = transaction.id

    response = client.delete(
        f"/api/budgets/{test_budget.id}/transactions/{transaction_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify transaction is deleted (hard delete)
    deleted_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    assert deleted_transaction is None


def test_delete_internal_transfer_deletes_both(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    second_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test that deleting an internal transfer deletes both linked transactions."""
    today = date.today()

    # Create linked transactions
    transaction1 = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-50000,
        description="Transfer out",
        status=TransactionStatus.CATEGORIZED,
        is_internal_transfer=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction1)
    db.flush()

    transaction2 = Transaction(
        account_id=second_account.id,
        date=today,
        amount=50000,
        description="Transfer in",
        status=TransactionStatus.CATEGORIZED,
        is_internal_transfer=True,
        counterpart_transaction_id=transaction1.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction2)
    db.flush()

    transaction1.counterpart_transaction_id = transaction2.id
    db.commit()

    transaction1_id = transaction1.id
    transaction2_id = transaction2.id

    # Expire objects from session before deletion to avoid detached instance issues
    db.expire_all()

    # Delete one transaction
    response = client.delete(
        f"/api/budgets/{test_budget.id}/transactions/{transaction1_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify both transactions are deleted (need fresh query after expiration)
    assert db.query(Transaction).filter(Transaction.id == transaction1_id).first() is None
    assert db.query(Transaction).filter(Transaction.id == transaction2_id).first() is None


def test_create_transaction_invalid_account(
    client: TestClient,
    test_budget: Budget,
    auth_headers: dict[str, str],
):
    """Test creating a transaction with invalid account ID."""
    today = date.today()
    fake_account_id = str(uuid.uuid4())

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions",
        json={
            "account_id": fake_account_id,
            "date": today.isoformat(),
            "amount": -10000,
            "description": "Test",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_access_transaction_from_different_budget(
    client: TestClient,
    db: Session,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test that users cannot access transactions from budgets they don't own."""
    # Create another user for the other budget
    other_user = User(
        email="inlineotheruser@example.com",
        password_hash="dummy_hash",
        email_verified=True,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    # Create a different budget owned by the other user
    other_budget = Budget(
        name="Other Budget",
        owner_id=other_user.id,
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(other_budget)
    db.commit()

    today = date.today()
    transaction = Transaction(
        account_id=test_account.id,
        date=today,
        amount=-10000,
        description="Test",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()

    # Try to access transaction via other budget (should fail because test_user doesn't own other_budget)
    response = client.get(
        f"/api/budgets/{other_budget.id}/transactions/{transaction.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_pagination(
    client: TestClient,
    db: Session,
    test_budget: Budget,
    test_account: Account,
    test_user: User,
    auth_headers: dict[str, str],
):
    """Test transaction pagination."""
    today = date.today()

    # Create 10 transactions
    for i in range(10):
        transaction = Transaction(
            account_id=test_account.id,
            date=today - timedelta(days=i),
            amount=-1000 * (i + 1),
            description=f"Transaction {i}",
            status=TransactionStatus.UNCATEGORIZED,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(transaction)
    db.commit()

    # Get first page with limit 5
    response = client.get(
        f"/api/budgets/{test_budget.id}/transactions?limit=5",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert data["next_cursor"] is not None

    # Get second page using cursor
    response2 = client.get(
        f"/api/budgets/{test_budget.id}/transactions?limit=5&cursor={data['next_cursor']}",
        headers=auth_headers,
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["data"]) == 5
    # Should have different transactions
    assert data["data"][0]["id"] != data2["data"][0]["id"]
