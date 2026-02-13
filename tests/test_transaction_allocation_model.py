"""Test TransactionAllocation model."""

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.models import (
    User, Budget, Account, Category, Transaction, BudgetPost,
    TransactionAllocation, AccountPurpose, AccountDatasource,
    BudgetPostType, TransactionStatus
)


@pytest.fixture
def test_data(db: Session):
    """Create test data for allocation tests."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email='test_allocation@example.com',
        password_hash='dummy_hash'
    )
    db.add(user)
    db.flush()

    # Create budget
    budget = Budget(
        id=uuid.uuid4(),
        name='Test Budget',
        owner_id=user.id,
        created_by=user.id
    )
    db.add(budget)
    db.flush()

    # Create account
    account = Account(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Test Account',
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        starting_balance=100000,
        currency='DKK',
        created_by=user.id,
        updated_by=user.id
    )
    db.add(account)
    db.flush()

    # Create category
    category = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Test Category',
        is_system=False,
        display_order=1,
        created_by=user.id
    )
    db.add(category)
    db.flush()

    # Create separate categories (UNIQUE constraint on category+period)
    category2 = Category(
        budget_id=budget.id,
        name="Category 2",
        display_order=2,
        created_by=user.id
    )
    db.add(category2)
    db.flush()

    # Create budget posts
    budget_post1 = BudgetPost(
        id=uuid.uuid4(),
        budget_id=budget.id,
        category_id=category.id,
        period_year=2026,
        period_month=2,
        type=BudgetPostType.FIXED,
        created_by=user.id,
        updated_by=user.id
    )
    budget_post2 = BudgetPost(
        id=uuid.uuid4(),
        budget_id=budget.id,
        category_id=category2.id,
        period_year=2026,
        period_month=2,
        type=BudgetPostType.CEILING,
        created_by=user.id,
        updated_by=user.id
    )
    db.add_all([budget_post1, budget_post2])
    db.flush()

    # Create amount patterns (not strictly necessary for allocation tests, but for completeness)
    from api.models.amount_pattern import AmountPattern
    amount_pattern1 = AmountPattern(
        budget_post_id=budget_post1.id,
        amount=10000,
        start_date=date(2026, 2, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=user.id,
        updated_by=user.id
    )
    amount_pattern2 = AmountPattern(
        budget_post_id=budget_post2.id,
        amount=15000,
        start_date=date(2026, 2, 1),
        end_date=None,
        recurrence_pattern={"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
        created_by=user.id,
        updated_by=user.id
    )
    db.add_all([amount_pattern1, amount_pattern2])
    db.flush()

    # Create transaction
    transaction = Transaction(
        id=uuid.uuid4(),
        account_id=account.id,
        date=date(2026, 2, 4),
        amount=-50000,  # -500.00 kr
        description='Test Transaction',
        status=TransactionStatus.UNCATEGORIZED,
        created_by=user.id,
        updated_by=user.id
    )
    db.add(transaction)
    db.flush()

    return {
        'user': user,
        'budget': budget,
        'account': account,
        'category': category,
        'budget_post1': budget_post1,
        'budget_post2': budget_post2,
        'transaction': transaction,
    }


def test_create_single_allocation(db: Session, test_data):
    """Test creating a single allocation (100% to one budget post)."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=50000,  # Full amount
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Verify allocation
    assert allocation.id is not None
    assert allocation.transaction_id == transaction.id
    assert allocation.budget_post_id == budget_post1.id
    assert allocation.amount == 50000
    assert allocation.is_remainder is True
    assert allocation.created_at is not None
    assert allocation.updated_at is not None


def test_transaction_allocation_relationship(db: Session, test_data):
    """Test relationship between transaction and allocations."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Refresh transaction and check relationship
    db.refresh(transaction)
    assert len(transaction.allocations) == 1
    assert transaction.allocations[0].id == allocation.id
    assert transaction.allocations[0].amount == 50000


def test_budget_post_allocation_relationship(db: Session, test_data):
    """Test relationship between budget post and allocations."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Refresh budget post and check relationship
    db.refresh(budget_post1)
    assert len(budget_post1.allocations) == 1
    assert budget_post1.allocations[0].id == allocation.id
    assert budget_post1.allocations[0].amount == 50000


def test_split_allocation(db: Session, test_data):
    """Test splitting transaction across multiple budget posts (80/20 split)."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']
    budget_post2 = test_data['budget_post2']

    # Create split allocations
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=40000,  # 80%
        is_remainder=False
    )
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post2.id,
        amount=10000,  # 20%
        is_remainder=True
    )
    db.add_all([allocation1, allocation2])
    db.flush()

    # Verify split
    db.refresh(transaction)
    assert len(transaction.allocations) == 2

    # Check total allocation
    total_allocated = sum(a.amount for a in transaction.allocations)
    assert total_allocated == abs(transaction.amount)


def test_unique_constraint_prevents_duplicate(db: Session, test_data):
    """Test that unique constraint prevents duplicate allocation to same budget post."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create first allocation
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=25000,
        is_remainder=False
    )
    db.add(allocation1)
    db.flush()

    # Attempt to create duplicate allocation
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,  # Same budget post
        amount=25000,
        is_remainder=False
    )
    db.add(allocation2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()

    assert 'uq_transaction_allocation_transaction_budget_post' in str(exc_info.value).lower() or 'unique' in str(exc_info.value).lower()


def test_cascade_delete_transaction(db: Session, test_data):
    """Test that deleting transaction cascades to delete allocations."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']
    budget_post2 = test_data['budget_post2']

    # Create allocations
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=30000,
        is_remainder=False
    )
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post2.id,
        amount=20000,
        is_remainder=True
    )
    db.add_all([allocation1, allocation2])
    db.flush()

    # Store allocation IDs
    allocation_ids = [allocation1.id, allocation2.id]

    # Delete transaction
    db.delete(transaction)
    db.flush()

    # Verify allocations are deleted
    remaining = db.query(TransactionAllocation).filter(
        TransactionAllocation.id.in_(allocation_ids)
    ).count()
    assert remaining == 0


def test_cascade_delete_budget_post(db: Session, test_data):
    """Test that deleting budget post cascades to delete allocations."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    allocation_id = allocation.id

    # Delete budget post
    db.delete(budget_post1)
    db.flush()

    # Verify allocation is deleted
    deleted_allocation = db.query(TransactionAllocation).filter(
        TransactionAllocation.id == allocation_id
    ).first()
    assert deleted_allocation is None


def test_remainder_flag(db: Session, test_data):
    """Test is_remainder flag functionality."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']
    budget_post2 = test_data['budget_post2']

    # Create allocation with remainder=False
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=30000,
        is_remainder=False
    )

    # Create allocation with remainder=True
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post2.id,
        amount=20000,
        is_remainder=True
    )

    db.add_all([allocation1, allocation2])
    db.flush()

    # Verify remainder flags
    assert allocation1.is_remainder is False
    assert allocation2.is_remainder is True


def test_allocation_repr(db: Session, test_data):
    """Test __repr__ method of TransactionAllocation."""
    transaction = test_data['transaction']
    budget_post1 = test_data['budget_post1']

    # Create allocation with remainder
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        budget_post_id=budget_post1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Check repr includes amount and remainder indicator
    repr_str = repr(allocation)
    assert '500.00 kr' in repr_str
    assert '(remainder)' in repr_str
    assert str(budget_post1.id) in repr_str
