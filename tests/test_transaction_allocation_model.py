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
from api.models.budget_post import BudgetPostDirection, CounterpartyType


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
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.FIXED,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=user.id,
        updated_by=user.id
    )
    budget_post2 = BudgetPost(
        id=uuid.uuid4(),
        budget_id=budget.id,
        category_id=category2.id,
        direction=BudgetPostDirection.EXPENSE,
        type=BudgetPostType.CEILING,
        accumulate=False,
        counterparty_type=CounterpartyType.EXTERNAL,
        created_by=user.id,
        updated_by=user.id
    )
    db.add_all([budget_post1, budget_post2])
    db.flush()

    # Create amount patterns for allocation tests
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
        'amount_pattern1': amount_pattern1,
        'amount_pattern2': amount_pattern2,
        'transaction': transaction,
    }


def test_create_single_allocation(db: Session, test_data):
    """Test creating a single allocation (100% to one amount pattern)."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=50000,  # Full amount
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Verify allocation
    assert allocation.id is not None
    assert allocation.transaction_id == transaction.id
    assert allocation.amount_pattern_id == amount_pattern1.id
    assert allocation.amount_occurrence_id is None
    assert allocation.amount == 50000
    assert allocation.is_remainder is True
    assert allocation.created_at is not None


def test_transaction_allocation_relationship(db: Session, test_data):
    """Test relationship between transaction and allocations."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
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


def test_amount_pattern_allocation_relationship(db: Session, test_data):
    """Test relationship between amount pattern and allocations."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Refresh amount pattern and check relationship
    db.refresh(amount_pattern1)
    assert len(amount_pattern1.allocations) == 1
    assert amount_pattern1.allocations[0].id == allocation.id
    assert amount_pattern1.allocations[0].amount == 50000


def test_split_allocation(db: Session, test_data):
    """Test splitting transaction across multiple amount patterns (80/20 split)."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']
    amount_pattern2 = test_data['amount_pattern2']

    # Create split allocations
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=40000,  # 80%
        is_remainder=False
    )
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern2.id,
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
    """Test that unique constraint prevents duplicate allocation to same amount pattern."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']

    # Create first allocation
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=25000,
        is_remainder=False
    )
    db.add(allocation1)
    db.flush()

    # Attempt to create duplicate allocation
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,  # Same amount pattern
        amount=25000,
        is_remainder=False
    )
    db.add(allocation2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()

    assert 'uq_transaction_allocation_transaction_pattern' in str(exc_info.value).lower() or 'unique' in str(exc_info.value).lower()


def test_cascade_delete_transaction(db: Session, test_data):
    """Test that deleting transaction cascades to delete allocations."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']
    amount_pattern2 = test_data['amount_pattern2']

    # Create allocations
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=30000,
        is_remainder=False
    )
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern2.id,
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


def test_cascade_delete_amount_pattern(db: Session, test_data):
    """Test that deleting amount pattern cascades to delete allocations."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']

    # Create allocation
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    allocation_id = allocation.id

    # Delete amount pattern
    db.delete(amount_pattern1)
    db.flush()

    # Verify allocation is deleted
    deleted_allocation = db.query(TransactionAllocation).filter(
        TransactionAllocation.id == allocation_id
    ).first()
    assert deleted_allocation is None


def test_remainder_flag(db: Session, test_data):
    """Test is_remainder flag functionality."""
    transaction = test_data['transaction']
    amount_pattern1 = test_data['amount_pattern1']
    amount_pattern2 = test_data['amount_pattern2']

    # Create allocation with remainder=False
    allocation1 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=30000,
        is_remainder=False
    )

    # Create allocation with remainder=True
    allocation2 = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern2.id,
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
    amount_pattern1 = test_data['amount_pattern1']

    # Create allocation with remainder
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=amount_pattern1.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Check repr includes amount and remainder indicator
    repr_str = repr(allocation)
    assert '500.00 kr' in repr_str
    assert '(remainder)' in repr_str
    assert 'pattern' in repr_str
    assert str(amount_pattern1.id) in repr_str


def test_check_constraint_exactly_one_target(db: Session, test_data):
    """Test that CHECK constraint enforces exactly one of pattern_id or occurrence_id."""
    transaction = test_data['transaction']

    # Test: both NULL - should fail
    allocation_both_null = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_pattern_id=None,
        amount_occurrence_id=None,
        amount=50000,
        is_remainder=False
    )
    db.add(allocation_both_null)

    with pytest.raises(IntegrityError) as exc_info:
        db.flush()

    assert 'ck_transaction_allocation_exactly_one_target' in str(exc_info.value).lower() or 'check' in str(exc_info.value).lower()


def test_allocation_to_amount_occurrence(db: Session, test_data):
    """Test creating an allocation to an amount occurrence (archived period)."""
    transaction = test_data['transaction']

    # Create archived budget post
    from api.models.archived_budget_post import ArchivedBudgetPost
    archived_post = ArchivedBudgetPost(
        budget_id=test_data['budget'].id,
        budget_post_id=test_data['budget_post1'].id,
        period_year=2026,
        period_month=2,
        direction=test_data['budget_post1'].direction,
        category_id=test_data['category'].id,
        type=test_data['budget_post1'].type,
        created_by=test_data['user'].id,
    )
    db.add(archived_post)
    db.flush()

    # Create amount occurrence
    from api.models.amount_occurrence import AmountOccurrence
    amount_occurrence = AmountOccurrence(
        archived_budget_post_id=archived_post.id,
        date=date(2026, 2, 5),
        amount=10000,
    )
    db.add(amount_occurrence)
    db.flush()

    # Create allocation to occurrence
    allocation = TransactionAllocation(
        id=uuid.uuid4(),
        transaction_id=transaction.id,
        amount_occurrence_id=amount_occurrence.id,
        amount=50000,
        is_remainder=True
    )
    db.add(allocation)
    db.flush()

    # Verify allocation
    assert allocation.amount_pattern_id is None
    assert allocation.amount_occurrence_id == amount_occurrence.id
    assert allocation.amount == 50000
    assert allocation.is_remainder is True

    # Verify relationship
    db.refresh(amount_occurrence)
    assert len(amount_occurrence.allocations) == 1
    assert amount_occurrence.allocations[0].id == allocation.id
