"""Tests for transaction allocation endpoint."""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.category import Category
from api.models.budget_post import BudgetPost, BudgetPostType, BudgetPostDirection, CounterpartyType
from api.models.amount_pattern import AmountPattern
from api.models.transaction import Transaction, TransactionStatus
from api.models.transaction_allocation import TransactionAllocation


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
        starting_balance=0,
        can_go_negative=False,
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
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def test_budget_posts_and_patterns(
    db: Session, test_budget: Budget, test_category: Category, test_account: Account, test_user: User
) -> tuple[list[BudgetPost], list[AmountPattern]]:
    """Create test budget posts and amount patterns."""
    # Create separate categories (UNIQUE constraint on category+period)
    groceries_category = Category(
        budget_id=test_budget.id,
        name="Groceries Category",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    household_category = Category(
        budget_id=test_budget.id,
        name="Household Category",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([groceries_category, household_category])
    db.flush()

    groceries = BudgetPost(
        budget_id=test_budget.id,
        category_id=groceries_category.id,
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.CEILING,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    household = BudgetPost(
        budget_id=test_budget.id,
        category_id=household_category.id,
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.CEILING,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )

    posts = [groceries, household]
    for post in posts:
        db.add(post)
    db.flush()

    # Create amount patterns
    today = date.today()
    groceries_pattern = AmountPattern(
        budget_post_id=groceries.id,
        amount=300000,  # 3000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    household_pattern = AmountPattern(
        budget_post_id=household.id,
        amount=100000,  # 1000 kr
        start_date=date(today.year, today.month, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    patterns = [groceries_pattern, household_pattern]
    db.add_all(patterns)
    db.commit()
    for post in posts:
        db.refresh(post)
    for pattern in patterns:
        db.refresh(pattern)
    return posts, patterns


@pytest.fixture
def test_transaction(db: Session, test_account: Account, test_user: User) -> Transaction:
    """Create a test transaction."""
    transaction = Transaction(
        account_id=test_account.id,
        date=date(2026, 2, 5),
        amount=-100000,  # -1000 kr expense
        description="Test store purchase",
        status=TransactionStatus.UNCATEGORIZED,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def test_allocate_single_budget_post(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test allocating transaction to a single amount pattern (100%)."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["amount_pattern_id"] == str(test_patterns[0].id)
    assert data["data"][0]["budget_post_id"] == str(test_budget_posts[0].id)
    assert data["data"][0]["amount"] == 100000
    assert data["data"][0]["is_remainder"] is False

    # Verify transaction status updated
    db.refresh(test_transaction)
    assert test_transaction.status == TransactionStatus.CATEGORIZED


def test_allocate_split_fixed_amounts(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test split allocation with fixed amounts (no remainder)."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 80000,  # 800 kr
                    "is_remainder": False,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": 20000,  # 200 kr
                    "is_remainder": False,
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2

    # Verify amounts
    amounts = {alloc["budget_post_id"]: alloc["amount"] for alloc in data["data"]}
    assert amounts[str(test_budget_posts[0].id)] == 80000
    assert amounts[str(test_budget_posts[1].id)] == 20000


def test_allocate_with_remainder(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test allocation with one budget post as remainder."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 60000,  # 600 kr fixed
                    "is_remainder": False,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": None,
                    "is_remainder": True,  # Should get 400 kr remainder
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2

    # Find allocations by budget post ID
    allocations = {alloc["budget_post_id"]: alloc for alloc in data["data"]}

    # Fixed allocation
    fixed_alloc = allocations[str(test_budget_posts[0].id)]
    assert fixed_alloc["amount"] == 60000
    assert fixed_alloc["is_remainder"] is False

    # Remainder allocation (should be calculated as 1000 - 600 = 400 kr)
    remainder_alloc = allocations[str(test_budget_posts[1].id)]
    assert remainder_alloc["amount"] == 40000
    assert remainder_alloc["is_remainder"] is True


def test_allocate_sum_exceeds_amount(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test validation: sum of allocations exceeds transaction amount."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 80000,
                    "is_remainder": False,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": 30000,  # Total 110000 > 100000
                    "is_remainder": False,
                },
            ]
        },
    )

    assert response.status_code == 422
    assert "must equal transaction amount" in response.json()["detail"]


def test_allocate_multiple_remainders(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test validation: only one allocation can be remainder."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": None,
                    "is_remainder": True,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": None,
                    "is_remainder": True,
                },
            ]
        },
    )

    assert response.status_code == 422
    assert "Only one allocation can be marked as remainder" in response.json()["detail"]


def test_allocate_remainder_negative(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test validation: remainder cannot be negative (over-allocation with remainder)."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 110000,  # More than transaction amount
                    "is_remainder": False,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": None,
                    "is_remainder": True,  # Would be -10000
                },
            ]
        },
    )

    assert response.status_code == 422
    assert "exceeds transaction amount" in response.json()["detail"]


def test_allocate_budget_post_not_in_budget(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, auth_headers: dict[str, str]
):
    """Test validation: budget post must belong to same budget."""
    import uuid

    headers = auth_headers

    # Use a random UUID that doesn't exist
    fake_pattern_id = str(uuid.uuid4())

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": fake_pattern_id,
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert "amount patterns not found" in response.json()["detail"]


def test_reallocate_replaces_existing(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test that re-allocating replaces existing allocations."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    # First allocation
    response1 = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )
    assert response1.status_code == 200

    # Verify first allocation in database
    count1 = db.query(TransactionAllocation).filter(
        TransactionAllocation.transaction_id == test_transaction.id
    ).count()
    assert count1 == 1

    # Second allocation (should replace)
    response2 = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 50000,
                    "is_remainder": False,
                },
                {
                    "amount_pattern_id": str(test_patterns[1].id),
                    "amount": 50000,
                    "is_remainder": False,
                },
            ]
        },
    )
    assert response2.status_code == 200

    # Verify old allocations were replaced
    count2 = db.query(TransactionAllocation).filter(
        TransactionAllocation.transaction_id == test_transaction.id
    ).count()
    assert count2 == 2


def test_clear_allocations(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test clearing allocations with empty array."""
    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    # First allocate
    response1 = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )
    assert response1.status_code == 200

    # Then clear
    response2 = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        headers=headers,
        json={"allocations": []},
    )
    assert response2.status_code == 200
    assert len(response2.json()["data"]) == 0

    # Verify status changed back to uncategorized
    db.refresh(test_transaction)
    assert test_transaction.status == TransactionStatus.UNCATEGORIZED

    # Verify no allocations in database
    count = db.query(TransactionAllocation).filter(
        TransactionAllocation.transaction_id == test_transaction.id
    ).count()
    assert count == 0


def test_allocate_transaction_not_found(
    client: TestClient, db: Session, test_user: User, test_budget: Budget, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]], auth_headers: dict[str, str]
):
    """Test allocation with non-existent transaction."""
    import uuid

    headers = auth_headers
    test_budget_posts, test_patterns = test_budget_posts_and_patterns
    fake_transaction_id = str(uuid.uuid4())

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{fake_transaction_id}/allocate",
        headers=headers,
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert "Transaction not found" in response.json()["detail"]


def test_allocate_unauthenticated(
    client: TestClient, db: Session, test_budget: Budget, test_transaction: Transaction, test_budget_posts_and_patterns: tuple[list[BudgetPost], list[AmountPattern]]
):
    """Test allocation without authentication."""
    test_budget_posts, test_patterns = test_budget_posts_and_patterns

    response = client.post(
        f"/api/budgets/{test_budget.id}/transactions/{test_transaction.id}/allocate",
        json={
            "allocations": [
                {
                    "amount_pattern_id": str(test_patterns[0].id),
                    "amount": 100000,
                    "is_remainder": False,
                }
            ]
        },
    )

    assert response.status_code == 401
