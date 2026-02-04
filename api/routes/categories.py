"""Category routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryReorderRequest,
)
from api.services.category_service import (
    get_budget_categories,
    build_category_tree,
    get_category_by_id,
    create_category,
    update_category,
    soft_delete_category,
    reorder_categories,
    get_children_count,
)
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets/{budget_id}/categories", tags=["categories"])


@router.get(
    "",
    response_model=CategoryTreeResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_categories(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CategoryTreeResponse:
    """
    List all categories for a budget as a hierarchical tree.

    Returns all non-deleted categories organized in a tree structure.
    User must own the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    categories = get_budget_categories(db, budget_uuid)
    tree = build_category_tree(categories)

    return CategoryTreeResponse(data=tree)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or parent category not found"},
        422: {"description": "Validation error"},
    },
)
def create_category_endpoint(
    budget_id: str,
    category_data: CategoryCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CategoryResponse:
    """
    Create a new category in a budget.

    Validates parent_id if provided and computes display_order if not specified.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Parse parent_id if provided
    parent_uuid = None
    if category_data.parent_id:
        try:
            parent_uuid = uuid.UUID(category_data.parent_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid parent_id format",
            )

    # Create category
    category = create_category(
        db=db,
        budget_id=budget_uuid,
        user_id=current_user.id,
        name=category_data.name,
        parent_id=parent_uuid,
        display_order=category_data.display_order,
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found",
        )

    return CategoryResponse(
        id=str(category.id),
        budget_id=str(category.budget_id),
        name=category.name,
        parent_id=str(category.parent_id) if category.parent_id else None,
        is_system=category.is_system,
        display_order=category.display_order,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.put(
    "/reorder",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to modify this budget"},
        404: {"description": "Budget or one or more categories not found"},
        422: {"description": "Validation error"},
    },
)
def reorder_categories_endpoint(
    budget_id: str,
    reorder_data: CategoryReorderRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    """
    Bulk update display_order for multiple categories.

    All category IDs must belong to the specified budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Parse and validate all category IDs
    items = []
    for item in reorder_data.items:
        try:
            category_uuid = uuid.UUID(item.id)
            items.append((category_uuid, item.display_order))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid category ID format: {item.id}",
            )

    # Reorder categories
    success = reorder_categories(db, budget_uuid, items)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more categories not found",
        )

    return {"message": "Categories reordered successfully"}

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or category not found"},
    },
)
def get_category(
    budget_id: str,
    category_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CategoryResponse:
    """
    Get a single category by ID.

    Returns 404 if category not found, soft-deleted, or doesn't belong to budget.
    Includes count of direct children.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        category_uuid = uuid.UUID(category_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or category not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Get category
    category = get_category_by_id(db, category_uuid, budget_uuid)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Get children count
    children_count = get_children_count(db, category_uuid)

    return CategoryResponse(
        id=str(category.id),
        budget_id=str(category.budget_id),
        name=category.name,
        parent_id=str(category.parent_id) if category.parent_id else None,
        is_system=category.is_system,
        display_order=category.display_order,
        created_at=category.created_at,
        updated_at=category.updated_at,
        children_count=children_count,
    )


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to modify this budget or circular reference detected"},
        404: {"description": "Budget or category not found"},
        422: {"description": "Validation error"},
    },
)
def update_category_endpoint(
    budget_id: str,
    category_id: str,
    category_data: CategoryUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CategoryResponse:
    """
    Update a category.

    Only the budget owner can update categories.
    Returns 404 if category not found or soft-deleted.
    Returns 403 if circular reference would be created.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        category_uuid = uuid.UUID(category_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or category not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Build updates dictionary with only fields that were provided
    updates = {}
    update_dict = category_data.model_dump(exclude_unset=True)

    # Handle name
    if 'name' in update_dict:
        updates['name'] = update_dict['name']

    # Handle parent_id - parse UUID if provided
    if 'parent_id' in update_dict:
        parent_id_value = update_dict['parent_id']
        if parent_id_value is None:
            # Explicitly set to null - make top-level
            updates['parent_id'] = None
        else:
            # Parse UUID string
            try:
                updates['parent_id'] = uuid.UUID(parent_id_value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid parent_id format",
                )

    # Handle display_order
    if 'display_order' in update_dict:
        updates['display_order'] = update_dict['display_order']

    # Update category
    category = update_category(
        db=db,
        category_id=category_uuid,
        budget_id=budget_uuid,
        user_id=current_user.id,
        updates=updates,
    )

    if not category:
        # Check if it exists to determine if it's a circular reference or not found
        existing = get_category_by_id(db, category_uuid, budget_uuid)
        if existing:
            # Category exists but update failed, likely circular reference
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot make category its own ancestor (circular reference)",
            )
        else:
            # Category doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

    return CategoryResponse(
        id=str(category.id),
        budget_id=str(category.budget_id),
        name=category.name,
        parent_id=str(category.parent_id) if category.parent_id else None,
        is_system=category.is_system,
        display_order=category.display_order,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this category or category is system category"},
        404: {"description": "Budget or category not found"},
    },
)
def delete_category(
    budget_id: str,
    category_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete a category and all its children.

    Only the budget owner can delete categories.
    Returns 403 if category is a system category.
    Returns 404 if category not found or already deleted.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        category_uuid = uuid.UUID(category_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or category not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check if category is system category before attempting delete
    category = get_category_by_id(db, category_uuid, budget_uuid)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system category",
        )

    # Delete category
    success = soft_delete_category(db, category_uuid, budget_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )


