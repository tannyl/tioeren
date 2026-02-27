"""Simplified tests for budget post hierarchy validation and cascade."""

import pytest
from sqlalchemy.orm import Session

from api.models.budget import Budget
from api.models.container import Container, ContainerType
from api.models.budget_post import BudgetPostDirection
from api.models.user import User
from api.services.budget_post_service import (
    create_budget_post,
    update_budget_post,
    BudgetPostValidationError,
)


@pytest.fixture
def test_user(db: Session) -> User:
    user = User(email="hierarchy_simple@example.com", password_hash="dummy_hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_budget(db: Session, test_user: User) -> Budget:
    budget = Budget(
        name="Hierarchy Test Budget",
        owner_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@pytest.fixture
def cashbox1(db: Session, test_budget: Budget, test_user: User) -> Container:
    container = Container(
        budget_id=test_budget.id,
        name="Cashbox 1",
        type=ContainerType.CASHBOX,
        starting_balance=100000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def cashbox2(db: Session, test_budget: Budget, test_user: User) -> Container:
    container = Container(
        budget_id=test_budget.id,
        name="Cashbox 2",
        type=ContainerType.CASHBOX,
        starting_balance=50000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def cashbox3(db: Session, test_budget: Budget, test_user: User) -> Container:
    container = Container(
        budget_id=test_budget.id,
        name="Cashbox 3",
        type=ContainerType.CASHBOX,
        starting_balance=25000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def piggybank(db: Session, test_budget: Budget, test_user: User) -> Container:
    container = Container(
        budget_id=test_budget.id,
        name="Piggybank X",
        type=ContainerType.PIGGYBANK,
        starting_balance=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def piggybank_y(db: Session, test_budget: Budget, test_user: User) -> Container:
    container = Container(
        budget_id=test_budget.id,
        name="Piggybank Y",
        type=ContainerType.PIGGYBANK,
        starting_balance=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


def test_create_child_with_valid_subset(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Child with subset of ancestor containers succeeds."""
    # Parent with all three
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id), str(cashbox2.id)],
        }],
    )
    assert parent is not None

    # Child with subset
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert child is not None
    assert set(child.container_ids) == {str(cashbox1.id), str(cashbox2.id)}


def test_create_child_with_superset_rejected(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Child with superset of ancestor containers is rejected."""
    # Parent with only two
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Try child with all three (superset)
    with pytest.raises(BudgetPostValidationError) as exc_info:
        create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Food", "Groceries"],
            container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
            amount_patterns=[{
                "amount": 50000,
                "start_date": "2026-01-01",
                "end_date": None,
                "container_ids": [str(cashbox1.id)],
            }],
        )
    assert "must be a subset of ancestor" in exc_info.value.message


def test_create_parent_over_children_cascades(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Creating parent over existing children cascades the narrowing."""
    # Children first with all three
    child1, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Parent with subset
    parent, affected = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Child should be cascaded
    assert len(affected) == 1
    assert str(child1.id) in [a["post_id"] for a in affected]

    db.refresh(child1)
    assert set(child1.container_ids) == {str(cashbox1.id), str(cashbox2.id)}


def test_update_parent_cascades_to_descendants(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Updating parent to narrow pool cascades to descendants."""
    # Parent with all three
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Child with all three
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Update parent to only cashbox1
    _, affected = update_budget_post(
        db=db,
        post_id=parent.id,
        budget_id=test_budget.id,
        user_id=test_user.id,
        container_ids=[str(cashbox1.id)],
    )

    # Child should be cascaded
    assert len(affected) == 1
    assert affected[0]["post_id"] == str(child.id)

    db.refresh(child)
    assert child.container_ids == [str(cashbox1.id)]


def test_cascade_cleans_amount_patterns(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Cascade also cleans amount patterns on descendants."""
    # Parent with all three
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Child with pattern using cashbox2 and cashbox3
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox2.id), str(cashbox3.id)],
        }],
    )

    # Update parent to only cashbox1
    _, affected = update_budget_post(
        db=db,
        post_id=parent.id,
        budget_id=test_budget.id,
        user_id=test_user.id,
        container_ids=[str(cashbox1.id)],
    )

    # Verify child's pattern was cleaned
    db.refresh(child)
    assert len(child.amount_patterns) == 1
    pattern = child.amount_patterns[0]
    # Pattern had no overlap with new pool, so gets child's full new pool
    assert pattern.container_ids == [str(cashbox1.id)]


def test_multi_level_cascade(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Cascade affects grandchildren too."""
    # Hierarchy: Food -> Groceries -> Vegetables
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    grandchild, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries", "Vegetables"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 25000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Update parent to only cashbox1
    _, affected = update_budget_post(
        db=db,
        post_id=parent.id,
        budget_id=test_budget.id,
        user_id=test_user.id,
        container_ids=[str(cashbox1.id)],
    )

    # Both child and grandchild should be affected
    assert len(affected) == 2
    affected_ids = {a["post_id"] for a in affected}
    assert str(child.id) in affected_ids
    assert str(grandchild.id) in affected_ids

    db.refresh(child)
    db.refresh(grandchild)
    assert child.container_ids == [str(cashbox1.id)]
    assert grandchild.container_ids == [str(cashbox1.id)]


def test_skip_level_ancestor_validation(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """C at ['A','B','C'], no B, but A exists -> C constrained by A."""
    # Parent at ["Food"] with cashbox1, cashbox2
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Grandchild (no intermediate) should be constrained by parent
    grandchild, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries", "Vegetables"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 25000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert grandchild is not None

    # Try to add cashbox3 (not in ancestor) - should fail
    with pytest.raises(BudgetPostValidationError) as exc_info:
        update_budget_post(
            db=db,
            post_id=grandchild.id,
            budget_id=test_budget.id,
            user_id=test_user.id,
            container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        )
    assert "must be a subset of ancestor" in exc_info.value.message


def test_cascade_with_intermediate_posts(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """A->B->C all exist, A narrows -> B narrowed first, then C against B's new pool."""
    # Create A with all three
    a, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )

    # Create B with cashbox2 and cashbox3
    b, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox2.id)],
        }],
    )

    # Create C with cashbox3
    c, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries", "Vegetables"],
        container_ids=[str(cashbox3.id)],
        amount_patterns=[{
            "amount": 25000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox3.id)],
        }],
    )

    # Update A to only cashbox1 and cashbox2
    _, affected = update_budget_post(
        db=db,
        post_id=a.id,
        budget_id=test_budget.id,
        user_id=test_user.id,
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
    )

    # B should be narrowed to cashbox2 (intersection)
    # C should be narrowed to [] -> gets B's new pool [cashbox2]
    assert len(affected) == 2

    db.refresh(b)
    db.refresh(c)
    assert set(b.container_ids) == {str(cashbox2.id)}
    # C's intersection is empty, so gets B's full new pool
    assert c.container_ids == [str(cashbox2.id)]


def test_piggybank_inheritance(
    db: Session,
    test_budget: Budget,
    test_user: User,
    piggybank: Container,
    piggybank_y: Container,
):
    """Create ancestor with piggybank X, create child - must use same piggybank. Try different piggybank -> rejected."""
    # Ancestor with piggybank X
    ancestor, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Savings"],
        container_ids=[str(piggybank.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(piggybank.id)],
        }],
    )
    assert ancestor is not None

    # Child with same piggybank - should succeed
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Savings", "Emergency Fund"],
        container_ids=[str(piggybank.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(piggybank.id)],
        }],
    )
    assert child is not None
    assert child.container_ids == [str(piggybank.id)]

    # Try child with different piggybank - should be rejected
    with pytest.raises(BudgetPostValidationError) as exc_info:
        create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Savings", "Vacation Fund"],
            container_ids=[str(piggybank_y.id)],
            amount_patterns=[{
                "amount": 30000,
                "start_date": "2026-01-01",
                "end_date": None,
                "container_ids": [str(piggybank_y.id)],
            }],
        )
    assert "must be a subset of ancestor" in exc_info.value.message


def test_root_level_no_ancestor_constraint(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
):
    """Root-level post (category_path length 1, e.g. ['Food']) has no ancestor constraint and can use any containers."""
    # Create root-level post with cashbox1
    root1, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert root1 is not None
    assert root1.container_ids == [str(cashbox1.id)]

    # Create another root-level post with cashbox2 - should succeed (no ancestor constraint)
    root2, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Transport"],
        container_ids=[str(cashbox2.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox2.id)],
        }],
    )
    assert root2 is not None
    assert root2.container_ids == [str(cashbox2.id)]


def test_different_directions_dont_interfere(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Income post at ['Salary'] with containers [A]. Expense post at ['Salary'] with containers [B, C]. Should succeed - different directions are independent hierarchies."""
    # Income post with cashbox1
    income_post, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.INCOME,
        category_path=["Salary"],
        container_ids=[str(cashbox1.id)],
        amount_patterns=[{
            "amount": 500000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert income_post is not None
    assert income_post.container_ids == [str(cashbox1.id)]

    # Expense post at same category path but different direction - should succeed with different containers
    expense_post, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Salary"],
        container_ids=[str(cashbox2.id), str(cashbox3.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox2.id)],
        }],
    )
    assert expense_post is not None
    assert set(expense_post.container_ids) == {str(cashbox2.id), str(cashbox3.id)}


def test_update_child_superset_rejected(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
    cashbox3: Container,
):
    """Create parent with [A, B]. Create child with [A]. Try to UPDATE child to [A, B, C] -> rejected because [C] is not in parent's pool."""
    # Parent with cashbox1, cashbox2
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert parent is not None

    # Child with cashbox1
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox1.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert child is not None

    # Try to update child to include cashbox3 (not in parent's pool) - should be rejected
    with pytest.raises(BudgetPostValidationError) as exc_info:
        update_budget_post(
            db=db,
            post_id=child.id,
            budget_id=test_budget.id,
            user_id=test_user.id,
            container_ids=[str(cashbox1.id), str(cashbox2.id), str(cashbox3.id)],
        )
    assert "must be a subset of ancestor" in exc_info.value.message


def test_empty_intersection_fallback(
    db: Session,
    test_budget: Budget,
    test_user: User,
    cashbox1: Container,
    cashbox2: Container,
):
    """Create parent with [A, B]. Create child with [B]. Update parent to [A] (removing B). Child's pool intersection with [A] is empty, so child should fallback to parent's full new pool [A]."""
    # Parent with cashbox1, cashbox2
    parent, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food"],
        container_ids=[str(cashbox1.id), str(cashbox2.id)],
        amount_patterns=[{
            "amount": 100000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox1.id)],
        }],
    )
    assert parent is not None

    # Child with cashbox2
    child, _ = create_budget_post(
        db=db,
        budget_id=test_budget.id,
        user_id=test_user.id,
        direction=BudgetPostDirection.EXPENSE,
        category_path=["Food", "Groceries"],
        container_ids=[str(cashbox2.id)],
        amount_patterns=[{
            "amount": 50000,
            "start_date": "2026-01-01",
            "end_date": None,
            "container_ids": [str(cashbox2.id)],
        }],
    )
    assert child is not None

    # Update parent to only cashbox1 (removing cashbox2)
    _, affected = update_budget_post(
        db=db,
        post_id=parent.id,
        budget_id=test_budget.id,
        user_id=test_user.id,
        container_ids=[str(cashbox1.id)],
    )

    # Child should be cascaded - intersection is empty, so gets parent's full new pool
    assert len(affected) == 1
    assert affected[0]["post_id"] == str(child.id)
    assert affected[0]["old_container_ids"] == [str(cashbox2.id)]
    assert affected[0]["new_container_ids"] == [str(cashbox1.id)]

    db.refresh(child)
    assert child.container_ids == [str(cashbox1.id)]
