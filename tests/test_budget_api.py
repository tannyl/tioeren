"""Tests for budget API endpoints."""

import uuid
import pytest
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.models.user import User
from api.models.budget import Budget
from api.models.category import Category


class TestListBudgets:
    """Tests for GET /api/budgets endpoint."""

    def test_list_empty(self, authenticated_client):
        """Empty list when user has no budgets."""
        response = authenticated_client.get("/api/budgets")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["next_cursor"] is None

    def test_list_single(self, authenticated_client, db: DBSession, test_user):
        """List returns single budget."""
        budget = Budget(
            name="Test Budget",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.get("/api/budgets")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test Budget"
        assert data["data"][0]["owner_id"] == str(test_user.id)
        assert data["next_cursor"] is None

    def test_list_pagination(self, authenticated_client, db: DBSession, test_user):
        """Test cursor pagination works."""
        # Create 3 budgets
        for i in range(3):
            budget = Budget(
                name=f"Budget {i}",
                owner_id=test_user.id,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            db.add(budget)
        db.commit()

        # Get first page with limit 2
        response = authenticated_client.get("/api/budgets?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["next_cursor"] is not None

        # Get second page using cursor
        cursor = data["next_cursor"]
        response = authenticated_client.get(f"/api/budgets?limit=2&cursor={cursor}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["next_cursor"] is None

    def test_list_excludes_soft_deleted(self, authenticated_client, db: DBSession, test_user):
        """Soft deleted budgets are not returned."""
        from datetime import datetime

        # Create active budget
        active = Budget(
            name="Active Budget",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(active)

        # Create soft deleted budget
        deleted = Budget(
            name="Deleted Budget",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
            deleted_at=datetime.now(UTC),
        )
        db.add(deleted)
        db.commit()

        response = authenticated_client.get("/api/budgets")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Active Budget"

    def test_list_requires_auth(self, client):
        """Listing budgets requires authentication."""
        response = client.get("/api/budgets")
        assert response.status_code == 401


class TestCreateBudget:
    """Tests for POST /api/budgets endpoint."""

    def test_create_success(self, authenticated_client, db: DBSession, test_user):
        """Successfully create budget returns 201."""
        response = authenticated_client.post(
            "/api/budgets",
            json={
                "name": "My Budget",
                "warning_threshold": 100000,  # 1000 kr in øre
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Budget"
        assert data["warning_threshold"] == 100000
        assert data["owner_id"] == str(test_user.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify budget exists in database
        budget_id = uuid.UUID(data["id"])
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        assert budget is not None
        assert budget.name == "My Budget"

    def test_create_default_categories_created(self, authenticated_client, db: DBSession, test_user):
        """Creating budget auto-creates default categories."""
        response = authenticated_client.post(
            "/api/budgets",
            json={"name": "Budget with Categories"},
        )

        assert response.status_code == 201
        budget_id = uuid.UUID(response.json()["id"])

        # Query categories for this budget
        categories = db.query(Category).filter(
            Category.budget_id == budget_id,
            Category.deleted_at.is_(None),
        ).all()

        # Check system categories exist
        category_names = [c.name for c in categories]
        assert "Indtægt" in category_names
        assert "Udgift" in category_names

        # Check subcategories exist
        assert "Løn" in category_names
        assert "Andet" in category_names
        assert "Bolig" in category_names
        assert "Husleje" in category_names
        assert "El" in category_names
        assert "Varme" in category_names
        assert "Forsikring" in category_names
        assert "Mad & dagligvarer" in category_names
        assert "Transport" in category_names
        assert "Abonnementer" in category_names
        assert "Sundhed" in category_names
        assert "Tøj" in category_names
        assert "Underholdning" in category_names

        # Verify hierarchy - Bolig should have parent Udgift
        bolig = next(c for c in categories if c.name == "Bolig")
        assert bolig.parent_id is not None
        udgift = db.query(Category).filter(Category.id == bolig.parent_id).first()
        assert udgift.name == "Udgift"

        # Verify system categories
        indtaegt = next(c for c in categories if c.name == "Indtægt")
        assert indtaegt.is_system is True
        udgift_cat = next(c for c in categories if c.name == "Udgift")
        assert udgift_cat.is_system is True

    def test_create_requires_auth(self, client):
        """Creating budget requires authentication."""
        response = client.post(
            "/api/budgets",
            json={"name": "Test Budget"},
        )
        assert response.status_code == 401

    def test_create_validates_name(self, authenticated_client):
        """Empty name is rejected."""
        response = authenticated_client.post(
            "/api/budgets",
            json={"name": ""},
        )
        assert response.status_code == 422

    def test_create_without_warning_threshold(self, authenticated_client):
        """Can create budget without warning threshold."""
        response = authenticated_client.post(
            "/api/budgets",
            json={"name": "No Threshold Budget"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["warning_threshold"] is None


class TestGetBudget:
    """Tests for GET /api/budgets/{id} endpoint."""

    def test_get_success(self, authenticated_client, db: DBSession, test_user):
        """Successfully get budget by ID."""
        budget = Budget(
            name="Get Test Budget",
            owner_id=test_user.id,
            warning_threshold=50000,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{budget.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(budget.id)
        assert data["name"] == "Get Test Budget"
        assert data["warning_threshold"] == 50000

    def test_get_not_found(self, authenticated_client):
        """Non-existent budget returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/budgets/{fake_id}")
        assert response.status_code == 404

    def test_get_forbidden_not_owner(self, authenticated_client, db: DBSession, other_user):
        """Cannot get budget owned by another user."""
        budget = Budget(
            name="Other User Budget",
            owner_id=other_user.id,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{budget.id}")
        assert response.status_code == 404  # Returns 404 to not leak existence

    def test_get_soft_deleted_returns_404(self, authenticated_client, db: DBSession, test_user):
        """Soft deleted budget returns 404."""
        from datetime import datetime

        budget = Budget(
            name="Deleted Budget",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
            deleted_at=datetime.now(UTC),
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.get(f"/api/budgets/{budget.id}")
        assert response.status_code == 404

    def test_get_requires_auth(self, client, db: DBSession, test_user):
        """Getting budget requires authentication."""
        budget = Budget(
            name="Auth Test Budget",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = client.get(f"/api/budgets/{budget.id}")
        assert response.status_code == 401

    def test_get_invalid_uuid(self, authenticated_client):
        """Invalid UUID returns 404."""
        response = authenticated_client.get("/api/budgets/not-a-uuid")
        assert response.status_code == 404


class TestUpdateBudget:
    """Tests for PUT /api/budgets/{id} endpoint."""

    def test_update_name(self, authenticated_client, db: DBSession, test_user):
        """Successfully update budget name."""
        budget = Budget(
            name="Old Name",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.put(
            f"/api/budgets/{budget.id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

        # Verify in database
        db.refresh(budget)
        assert budget.name == "New Name"

    def test_update_warning_threshold(self, authenticated_client, db: DBSession, test_user):
        """Successfully update warning threshold."""
        budget = Budget(
            name="Threshold Test",
            owner_id=test_user.id,
            warning_threshold=10000,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.put(
            f"/api/budgets/{budget.id}",
            json={"warning_threshold": 20000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["warning_threshold"] == 20000

    def test_update_both_fields(self, authenticated_client, db: DBSession, test_user):
        """Update both name and threshold."""
        budget = Budget(
            name="Old",
            owner_id=test_user.id,
            warning_threshold=10000,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.put(
            f"/api/budgets/{budget.id}",
            json={
                "name": "New",
                "warning_threshold": 30000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New"
        assert data["warning_threshold"] == 30000

    def test_update_forbidden_not_owner(self, authenticated_client, db: DBSession, other_user):
        """Cannot update budget owned by another user."""
        budget = Budget(
            name="Other Budget",
            owner_id=other_user.id,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.put(
            f"/api/budgets/{budget.id}",
            json={"name": "Hacked"},
        )
        assert response.status_code == 404  # Returns 404 to not leak existence

    def test_update_not_found(self, authenticated_client):
        """Updating non-existent budget returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.put(
            f"/api/budgets/{fake_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    def test_update_requires_auth(self, client, db: DBSession, test_user):
        """Updating budget requires authentication."""
        budget = Budget(
            name="Auth Test",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = client.put(
            f"/api/budgets/{budget.id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 401

    def test_update_validates_name(self, authenticated_client, db: DBSession, test_user):
        """Empty name is rejected."""
        budget = Budget(
            name="Valid Name",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.put(
            f"/api/budgets/{budget.id}",
            json={"name": ""},
        )
        assert response.status_code == 422


class TestDeleteBudget:
    """Tests for DELETE /api/budgets/{id} endpoint."""

    def test_delete_success(self, authenticated_client, db: DBSession, test_user):
        """Successfully soft delete budget."""
        budget = Budget(
            name="To Delete",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()
        budget_id = budget.id

        response = authenticated_client.delete(f"/api/budgets/{budget_id}")
        assert response.status_code == 204

        # Verify soft delete in database
        db.refresh(budget)
        assert budget.deleted_at is not None

        # Verify budget no longer appears in list
        list_response = authenticated_client.get("/api/budgets")
        data = list_response.json()
        assert len(data["data"]) == 0

    def test_delete_forbidden_not_owner(self, authenticated_client, db: DBSession, other_user):
        """Cannot delete budget owned by another user."""
        budget = Budget(
            name="Other Budget",
            owner_id=other_user.id,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.delete(f"/api/budgets/{budget.id}")
        assert response.status_code == 404  # Returns 404 to not leak existence

    def test_delete_not_found(self, authenticated_client):
        """Deleting non-existent budget returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(f"/api/budgets/{fake_id}")
        assert response.status_code == 404

    def test_delete_requires_auth(self, client, db: DBSession, test_user):
        """Deleting budget requires authentication."""
        budget = Budget(
            name="Auth Test",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(budget)
        db.commit()

        response = client.delete(f"/api/budgets/{budget.id}")
        assert response.status_code == 401

    def test_delete_already_deleted(self, authenticated_client, db: DBSession, test_user):
        """Deleting already deleted budget returns 404."""
        from datetime import datetime

        budget = Budget(
            name="Already Deleted",
            owner_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
            deleted_at=datetime.now(UTC),
        )
        db.add(budget)
        db.commit()

        response = authenticated_client.delete(f"/api/budgets/{budget.id}")
        assert response.status_code == 404
