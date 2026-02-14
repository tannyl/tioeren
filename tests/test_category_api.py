"""Tests for Category CRUD API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.models.category import Category
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
def parent_category(db: DBSession, test_budget: Budget, test_user: User) -> Category:
    """Create a parent category."""
    category = Category(
        budget_id=test_budget.id,
        name="Parent Category",
        is_system=False,
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def child_category(db: DBSession, test_budget: Budget, parent_category: Category, test_user: User) -> Category:
    """Create a child category."""
    category = Category(
        budget_id=test_budget.id,
        name="Child Category",
        parent_id=parent_category.id,
        is_system=False,
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def system_category(db: DBSession, test_budget: Budget, test_user: User) -> Category:
    """Create a system category."""
    category = Category(
        budget_id=test_budget.id,
        name="System Category",
        is_system=True,
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# GET /categories (tree)


def test_list_categories_returns_tree(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
    child_category: Category,
):
    """Test listing categories returns hierarchical tree structure."""
    response = authenticated_client.get(f"/api/budgets/{test_budget.id}/categories")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

    # Find parent in tree
    parent_node = next((c for c in data["data"] if c["id"] == str(parent_category.id)), None)
    assert parent_node is not None
    assert parent_node["name"] == "Parent Category"
    assert "children" in parent_node
    assert len(parent_node["children"]) == 1

    # Check child
    child_node = parent_node["children"][0]
    assert child_node["id"] == str(child_category.id)
    assert child_node["name"] == "Child Category"
    assert child_node["parent_id"] == str(parent_category.id)


def test_list_categories_requires_auth(client: TestClient, test_budget: Budget):
    """Test listing categories requires authentication."""
    response = client.get(f"/api/budgets/{test_budget.id}/categories")
    assert response.status_code == 401


def test_list_categories_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    other_budget: Budget,
):
    """Test user cannot list categories from other user's budget."""
    response = authenticated_client.get(f"/api/budgets/{other_budget.id}/categories")

    assert response.status_code == 404


def test_list_categories_excludes_deleted(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test soft-deleted categories are not included in tree."""
    # Soft delete the category
    from datetime import datetime, UTC
    parent_category.deleted_at = datetime.now(UTC)
    db.commit()

    response = authenticated_client.get(f"/api/budgets/{test_budget.id}/categories")

    assert response.status_code == 200
    data = response.json()

    # Check deleted category is not in results
    category_ids = [c["id"] for c in data["data"]]
    assert str(parent_category.id) not in category_ids


# POST /categories


def test_create_category(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test creating a basic category."""
    response = authenticated_client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={"name": "New Category"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Category"
    assert data["budget_id"] == str(test_budget.id)
    assert data["parent_id"] is None
    assert data["is_system"] is False


def test_create_category_with_parent(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test creating a child category."""
    response = authenticated_client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={
            "name": "Child Category",
            "parent_id": str(parent_category.id),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Child Category"
    assert data["parent_id"] == str(parent_category.id)


def test_create_category_auto_display_order(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test display_order is auto-incremented."""
    # Create first category
    response1 = authenticated_client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={"name": "Category 1"},
    )
    assert response1.status_code == 201
    data1 = response1.json()

    # Create second category
    response2 = authenticated_client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={"name": "Category 2"},
    )
    assert response2.status_code == 201
    data2 = response2.json()

    # Second should have higher display_order
    assert data2["display_order"] > data1["display_order"]


def test_create_category_requires_auth(client: TestClient, test_budget: Budget):
    """Test creating category requires authentication."""
    response = client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={"name": "New Category"},
    )
    assert response.status_code == 401


def test_create_category_validates_parent(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test creating category with invalid parent_id fails."""
    # Try to create with non-existent parent
    fake_uuid = str(uuid.uuid4())
    response = authenticated_client.post(
        f"/api/budgets/{test_budget.id}/categories",
        json={
            "name": "Child Category",
            "parent_id": fake_uuid,
        },
    )

    assert response.status_code == 404


def test_create_category_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    other_budget: Budget,
):
    """Test user cannot create category in other user's budget."""
    response = authenticated_client.post(
        f"/api/budgets/{other_budget.id}/categories",
        json={"name": "New Category"},
    )

    assert response.status_code == 404


# GET /categories/{id}


def test_get_category(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
    child_category: Category,
):
    """Test getting a single category."""
    response = authenticated_client.get(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(parent_category.id)
    assert data["name"] == "Parent Category"
    assert data["children_count"] == 1


def test_get_category_not_found(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test getting non-existent category returns 404."""
    fake_uuid = uuid.uuid4()
    response = authenticated_client.get(f"/api/budgets/{test_budget.id}/categories/{fake_uuid}")

    assert response.status_code == 404


def test_get_category_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    other_budget: Budget,
    other_user: User,
):
    """Test user cannot get category from other user's budget."""
    # Create category in other's budget
    other_category = Category(
        budget_id=other_budget.id,
        name="Other Category",
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(other_category)
    db.commit()

    response = authenticated_client.get(
        f"/api/budgets/{test_budget.id}/categories/{other_category.id}"
    )

    assert response.status_code == 404


# PUT /categories/{id}


def test_update_category_name(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test updating category name."""
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"


def test_update_category_parent(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test moving category to different parent."""
    # Create new parent
    new_parent = Category(
        budget_id=test_budget.id,
        name="New Parent",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(new_parent)
    db.commit()

    # Create category to move
    category_to_move = Category(
        budget_id=test_budget.id,
        name="Move Me",
        parent_id=parent_category.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(category_to_move)
    db.commit()

    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/{category_to_move.id}",
        json={"parent_id": str(new_parent.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] == str(new_parent.id)


def test_update_category_display_order(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test changing category display order."""
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}",
        json={"display_order": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_order"] == 10


def test_update_category_remove_parent(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
    child_category: Category,
):
    """Test removing parent_id to make a child category top-level."""
    # Verify child starts with parent
    response = authenticated_client.get(
        f"/api/budgets/{test_budget.id}/categories/{child_category.id}"
    )
    assert response.status_code == 200
    assert response.json()["parent_id"] == str(parent_category.id)

    # Update to remove parent (set to null)
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/{child_category.id}",
        json={"parent_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] is None
    assert data["name"] == "Child Category"

    # Verify in database
    db.refresh(child_category)
    assert child_category.parent_id is None


def test_update_category_prevents_circular(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
    child_category: Category,
):
    """Test circular reference prevention."""
    # Try to make parent a child of its own child (circular)
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}",
        json={"parent_id": str(child_category.id)},
    )

    assert response.status_code == 403
    assert "circular" in response.json()["detail"].lower()


def test_update_category_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    other_budget: Budget,
    other_user: User,
):
    """Test user cannot update category in other user's budget."""
    # Create category in other's budget
    other_category = Category(
        budget_id=other_budget.id,
        name="Other Category",
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(other_category)
    db.commit()

    response = authenticated_client.put(
        f"/api/budgets/{other_budget.id}/categories/{other_category.id}",
        json={"name": "Hacked Name"},
    )

    assert response.status_code == 404


# DELETE /categories/{id}


def test_delete_category(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
):
    """Test soft deleting a category."""
    response = authenticated_client.delete(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}"
    )

    assert response.status_code == 204

    # Verify category is soft-deleted
    db.refresh(parent_category)
    assert parent_category.deleted_at is not None


def test_delete_category_cascades_to_children(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    parent_category: Category,
    child_category: Category,
):
    """Test deleting category also deletes all children."""
    response = authenticated_client.delete(
        f"/api/budgets/{test_budget.id}/categories/{parent_category.id}"
    )

    assert response.status_code == 204

    # Verify both parent and child are soft-deleted
    db.refresh(parent_category)
    db.refresh(child_category)
    assert parent_category.deleted_at is not None
    assert child_category.deleted_at is not None


def test_delete_category_protects_system(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
    system_category: Category,
):
    """Test system categories cannot be deleted."""
    response = authenticated_client.delete(
        f"/api/budgets/{test_budget.id}/categories/{system_category.id}"
    )

    assert response.status_code == 403
    assert "system" in response.json()["detail"].lower()

    # Verify category is NOT deleted
    db.refresh(system_category)
    assert system_category.deleted_at is None


def test_delete_category_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    other_budget: Budget,
    other_user: User,
):
    """Test user cannot delete category in other user's budget."""
    # Create category in other's budget
    other_category = Category(
        budget_id=other_budget.id,
        name="Other Category",
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(other_category)
    db.commit()

    response = authenticated_client.delete(
        f"/api/budgets/{other_budget.id}/categories/{other_category.id}"
    )

    assert response.status_code == 404


# PUT /categories/reorder


def test_reorder_categories(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test bulk reordering categories."""
    # Create multiple categories
    cat1 = Category(
        budget_id=test_budget.id,
        name="Cat 1",
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    cat2 = Category(
        budget_id=test_budget.id,
        name="Cat 2",
        display_order=1,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([cat1, cat2])
    db.commit()

    # Reorder them
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/reorder",
        json={
            "items": [
                {"id": str(cat1.id), "display_order": 10},
                {"id": str(cat2.id), "display_order": 5},
            ]
        },
    )

    assert response.status_code == 200

    # Verify new order
    db.refresh(cat1)
    db.refresh(cat2)
    assert cat1.display_order == 10
    assert cat2.display_order == 5


def test_reorder_categories_validates_ids(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test reorder fails if any ID is invalid."""
    fake_uuid = uuid.uuid4()
    response = authenticated_client.put(
        f"/api/budgets/{test_budget.id}/categories/reorder",
        json={
            "items": [
                {"id": str(fake_uuid), "display_order": 10},
            ]
        },
    )

    assert response.status_code == 404


def test_reorder_categories_requires_ownership(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    other_budget: Budget,
    other_user: User,
):
    """Test user cannot reorder categories in other user's budget."""
    # Create category in other's budget
    other_category = Category(
        budget_id=other_budget.id,
        name="Other Category",
        created_by=other_user.id,
        updated_by=other_user.id,
    )
    db.add(other_category)
    db.commit()

    response = authenticated_client.put(
        f"/api/budgets/{other_budget.id}/categories/reorder",
        json={
            "items": [
                {"id": str(other_category.id), "display_order": 10},
            ]
        },
    )

    assert response.status_code == 404


# Tree building and helpers


def test_tree_building_multiple_levels(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test tree building with 3 levels of hierarchy."""
    # Create 3-level hierarchy
    level1 = Category(
        budget_id=test_budget.id,
        name="Level 1",
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(level1)
    db.commit()

    level2 = Category(
        budget_id=test_budget.id,
        name="Level 2",
        parent_id=level1.id,
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(level2)
    db.commit()

    level3 = Category(
        budget_id=test_budget.id,
        name="Level 3",
        parent_id=level2.id,
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(level3)
    db.commit()

    response = authenticated_client.get(f"/api/budgets/{test_budget.id}/categories")

    assert response.status_code == 200
    data = response.json()

    # Navigate the tree
    level1_node = next((c for c in data["data"] if c["name"] == "Level 1"), None)
    assert level1_node is not None
    assert len(level1_node["children"]) == 1

    level2_node = level1_node["children"][0]
    assert level2_node["name"] == "Level 2"
    assert len(level2_node["children"]) == 1

    level3_node = level2_node["children"][0]
    assert level3_node["name"] == "Level 3"
    assert len(level3_node["children"]) == 0


def test_tree_building_sorting(
    authenticated_client: TestClient,
    db: DBSession,
    test_user: User,
    test_budget: Budget,
):
    """Test tree respects display_order at each level."""
    # Create categories with specific order
    cat1 = Category(
        budget_id=test_budget.id,
        name="Should be second",
        display_order=1,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    cat2 = Category(
        budget_id=test_budget.id,
        name="Should be first",
        display_order=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    cat3 = Category(
        budget_id=test_budget.id,
        name="Should be third",
        display_order=2,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add_all([cat1, cat2, cat3])
    db.commit()

    response = authenticated_client.get(f"/api/budgets/{test_budget.id}/categories")

    assert response.status_code == 200
    data = response.json()

    # Verify order
    names = [c["name"] for c in data["data"]]
    assert names == ["Should be first", "Should be second", "Should be third"]


def test_circular_reference_detection(
    db: DBSession,
    test_budget: Budget,
    test_user: User,
):
    """Test circular reference detection helper function."""
    from api.services.category_service import detect_circular_reference

    # Create chain: A -> B -> C
    cat_a = Category(
        budget_id=test_budget.id,
        name="A",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(cat_a)
    db.commit()

    cat_b = Category(
        budget_id=test_budget.id,
        name="B",
        parent_id=cat_a.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(cat_b)
    db.commit()

    cat_c = Category(
        budget_id=test_budget.id,
        name="C",
        parent_id=cat_b.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(cat_c)
    db.commit()

    # Try to make A a child of C (would create cycle: A -> B -> C -> A)
    is_circular = detect_circular_reference(db, cat_a.id, cat_c.id)
    assert is_circular is True

    # Try to make A a child of B (would create cycle: A -> B -> A)
    is_circular = detect_circular_reference(db, cat_a.id, cat_b.id)
    assert is_circular is True

    # Try to make C a child of A (valid, no cycle)
    is_circular = detect_circular_reference(db, cat_c.id, cat_a.id)
    assert is_circular is False
