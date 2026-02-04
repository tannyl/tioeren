"""Category service layer for business logic."""

import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict

from sqlalchemy.orm import Session

from api.models.category import Category


def get_budget_categories(
    db: Session,
    budget_id: uuid.UUID,
) -> List[Category]:
    """
    Get all non-deleted categories for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to get categories for

    Returns:
        List of Category instances ordered by display_order
    """
    return db.query(Category).filter(
        Category.budget_id == budget_id,
        Category.deleted_at.is_(None),
    ).order_by(Category.display_order).all()


def build_category_tree(categories: List[Category]) -> List[Dict]:
    """
    Build hierarchical tree from flat list of categories.

    Args:
        categories: Flat list of Category instances

    Returns:
        List of dicts with 'category' and 'children' keys representing tree structure
    """
    # Group categories by parent_id
    children_map: Dict[Optional[uuid.UUID], List[Category]] = {}
    for cat in categories:
        parent_key = cat.parent_id
        if parent_key not in children_map:
            children_map[parent_key] = []
        children_map[parent_key].append(cat)

    # Sort each level by display_order
    for children_list in children_map.values():
        children_list.sort(key=lambda c: c.display_order)

    def build_node(category: Category) -> Dict:
        """Recursively build tree node."""
        node = {
            'id': str(category.id),
            'budget_id': str(category.budget_id),
            'name': category.name,
            'parent_id': str(category.parent_id) if category.parent_id else None,
            'is_system': category.is_system,
            'display_order': category.display_order,
            'created_at': category.created_at,
            'updated_at': category.updated_at,
            'children': []
        }

        # Add children if any
        if category.id in children_map:
            node['children'] = [build_node(child) for child in children_map[category.id]]

        return node

    # Build tree from root categories (parent_id is None)
    root_categories = children_map.get(None, [])
    return [build_node(cat) for cat in root_categories]


def get_category_by_id(
    db: Session,
    category_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Optional[Category]:
    """
    Get a single category by ID.

    Args:
        db: Database session
        category_id: Category ID to retrieve
        budget_id: Budget ID (for authorization check)

    Returns:
        Category if found and belongs to budget, None otherwise
    """
    return db.query(Category).filter(
        Category.id == category_id,
        Category.budget_id == budget_id,
        Category.deleted_at.is_(None),
    ).first()


def get_max_display_order(
    db: Session,
    budget_id: uuid.UUID,
    parent_id: Optional[uuid.UUID] = None,
) -> int:
    """
    Get the maximum display_order among siblings.

    Args:
        db: Database session
        budget_id: Budget ID
        parent_id: Parent category ID (None for root level)

    Returns:
        Maximum display_order value, or -1 if no siblings exist
    """
    query = db.query(Category).filter(
        Category.budget_id == budget_id,
        Category.deleted_at.is_(None),
    )

    if parent_id is None:
        query = query.filter(Category.parent_id.is_(None))
    else:
        query = query.filter(Category.parent_id == parent_id)

    categories = query.all()
    if not categories:
        return -1

    return max(cat.display_order for cat in categories)


def create_category(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    parent_id: Optional[uuid.UUID] = None,
    display_order: Optional[int] = None,
) -> Optional[Category]:
    """
    Create a new category.

    Args:
        db: Database session
        budget_id: Budget ID to create category in
        user_id: User ID creating the category
        name: Category name
        parent_id: Optional parent category ID
        display_order: Optional display order (computed if not provided)

    Returns:
        Created Category instance, or None if parent validation fails
    """
    # Validate parent_id if provided
    if parent_id is not None:
        parent = get_category_by_id(db, parent_id, budget_id)
        if not parent:
            return None

    # Compute display_order if not provided
    if display_order is None:
        max_order = get_max_display_order(db, budget_id, parent_id)
        display_order = max_order + 1

    category = Category(
        budget_id=budget_id,
        name=name,
        parent_id=parent_id,
        display_order=display_order,
        is_system=False,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


def detect_circular_reference(
    db: Session,
    category_id: uuid.UUID,
    new_parent_id: uuid.UUID,
) -> bool:
    """
    Check if setting new_parent_id would create a circular reference.

    Args:
        db: Database session
        category_id: Category ID to update
        new_parent_id: New parent ID to check

    Returns:
        True if circular reference would be created, False otherwise
    """
    # Walk up the parent chain from new_parent_id
    current_id = new_parent_id
    visited = set()

    while current_id is not None:
        # Check if we've encountered the category we're trying to update
        if current_id == category_id:
            return True

        # Prevent infinite loops (shouldn't happen with valid data)
        if current_id in visited:
            return True
        visited.add(current_id)

        # Get parent
        category = db.query(Category).filter(
            Category.id == current_id,
            Category.deleted_at.is_(None),
        ).first()

        if not category:
            break

        current_id = category.parent_id

    return False


def update_category(
    db: Session,
    category_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    updates: dict,
) -> Optional[Category]:
    """
    Update a category.

    Args:
        db: Database session
        category_id: Category ID to update
        budget_id: Budget ID (for authorization check)
        user_id: User ID updating the category
        updates: Dictionary of fields to update (only includes fields that were explicitly provided)

    Returns:
        Updated Category if found and belongs to budget, None otherwise
    """
    category = get_category_by_id(db, category_id, budget_id)
    if not category:
        return None

    # Check for circular reference if parent_id is changing
    if 'parent_id' in updates:
        new_parent_id = updates['parent_id']

        # Only validate if setting to a non-null parent
        if new_parent_id is not None:
            if detect_circular_reference(db, category_id, new_parent_id):
                return None

            # Validate parent exists and belongs to same budget
            parent = get_category_by_id(db, new_parent_id, budget_id)
            if not parent:
                return None

        # Update parent_id (can be None to make root-level)
        category.parent_id = new_parent_id

    # Update other fields if provided
    if 'name' in updates:
        category.name = updates['name']
    if 'display_order' in updates:
        category.display_order = updates['display_order']

    category.updated_by = user_id

    db.commit()
    db.refresh(category)

    return category


def cascade_soft_delete_children(
    db: Session,
    parent_id: uuid.UUID,
) -> None:
    """
    Recursively soft-delete all children of a category.

    Args:
        db: Database session
        parent_id: Parent category ID whose children should be deleted
    """
    children = db.query(Category).filter(
        Category.parent_id == parent_id,
        Category.deleted_at.is_(None),
    ).all()

    now = datetime.now(UTC)
    for child in children:
        child.deleted_at = now
        # Recursively delete children
        cascade_soft_delete_children(db, child.id)


def soft_delete_category(
    db: Session,
    category_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> bool:
    """
    Soft delete a category and all its children.

    Args:
        db: Database session
        category_id: Category ID to delete
        budget_id: Budget ID (for authorization check)

    Returns:
        True if category was deleted, False if not found, not in budget, or is_system=True
    """
    category = get_category_by_id(db, category_id, budget_id)
    if not category:
        return False

    # Cannot delete system categories
    if category.is_system:
        return False

    # Soft delete the category
    now = datetime.now(UTC)
    category.deleted_at = now

    # Cascade to children
    cascade_soft_delete_children(db, category_id)

    db.commit()

    return True


def reorder_categories(
    db: Session,
    budget_id: uuid.UUID,
    items: List[tuple[uuid.UUID, int]],
) -> bool:
    """
    Bulk update display_order for multiple categories.

    Args:
        db: Database session
        budget_id: Budget ID (for authorization check)
        items: List of (category_id, new_display_order) tuples

    Returns:
        True if all categories were updated, False if any not found
    """
    for category_id, new_display_order in items:
        category = get_category_by_id(db, category_id, budget_id)
        if not category:
            return False
        category.display_order = new_display_order

    db.commit()

    return True


def get_children_count(
    db: Session,
    category_id: uuid.UUID,
) -> int:
    """
    Get the count of direct children for a category.

    Args:
        db: Database session
        category_id: Category ID to count children for

    Returns:
        Number of non-deleted children
    """
    return db.query(Category).filter(
        Category.parent_id == category_id,
        Category.deleted_at.is_(None),
    ).count()
