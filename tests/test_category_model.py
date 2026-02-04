"""Test Category model hierarchical relationships."""
import uuid
import pytest
from sqlalchemy.orm import Session

from api.models import Category, Budget, User


def test_category_parent_child_relationship(db: Session):
    """Test that parent-child relationships work correctly."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email='test_categories@example.com',
        password_hash='dummy_hash'
    )
    db.add(user)
    db.flush()
    
    # Create test budget
    budget = Budget(
        id=uuid.uuid4(),
        name='Test Budget',
        owner_id=user.id,
        created_by=user.id
    )
    db.add(budget)
    db.flush()
    
    # Create parent category
    parent = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Indtægt',
        is_system=True,
        display_order=1,
        created_by=user.id
    )
    db.add(parent)
    db.flush()
    
    # Create child categories
    child1 = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Løn',
        parent_id=parent.id,
        is_system=False,
        display_order=1,
        created_by=user.id
    )
    child2 = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Andet',
        parent_id=parent.id,
        is_system=False,
        display_order=2,
        created_by=user.id
    )
    db.add(child1)
    db.add(child2)
    db.flush()
    
    # Refresh and verify parent has children
    db.refresh(parent)
    assert len(parent.children) == 2
    assert parent.children[0].name == 'Løn'  # Should be ordered by display_order
    assert parent.children[1].name == 'Andet'
    
    # Verify child has parent
    db.refresh(child1)
    assert child1.parent is not None
    assert child1.parent.name == 'Indtægt'
    
    # Verify budget relationship
    assert len(budget.categories) == 3


def test_category_cascade_delete(db: Session):
    """Test that deleting parent cascades to children."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email='test_cascade@example.com',
        password_hash='dummy_hash'
    )
    db.add(user)
    db.flush()
    
    # Create test budget
    budget = Budget(
        id=uuid.uuid4(),
        name='Test Budget',
        owner_id=user.id,
        created_by=user.id
    )
    db.add(budget)
    db.flush()
    
    # Create parent and child
    parent = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Parent',
        is_system=False,
        display_order=1,
        created_by=user.id
    )
    db.add(parent)
    db.flush()
    
    child = Category(
        id=uuid.uuid4(),
        budget_id=budget.id,
        name='Child',
        parent_id=parent.id,
        is_system=False,
        display_order=1,
        created_by=user.id
    )
    db.add(child)
    db.flush()
    
    child_id = child.id
    
    # Delete parent
    db.delete(parent)
    db.flush()
    
    # Verify child is also deleted
    deleted_child = db.query(Category).filter(Category.id == child_id).first()
    assert deleted_child is None
