"""Category schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Request schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[str] = Field(None, description="Parent category ID (UUID)")
    display_order: Optional[int] = Field(None, description="Display order among siblings")


class CategoryUpdate(BaseModel):
    """Request schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[str] = Field(None, description="Parent category ID (UUID), null to make top-level")
    display_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """Response schema for a single category."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str
    name: str
    parent_id: Optional[str]
    is_system: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    children_count: Optional[int] = Field(None, description="Number of direct children (only in single get)")


class CategoryTreeNode(BaseModel):
    """Recursive tree node for category hierarchy."""

    id: str
    budget_id: str
    name: str
    parent_id: Optional[str]
    is_system: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    children: List['CategoryTreeNode'] = Field(default_factory=list)


class CategoryTreeResponse(BaseModel):
    """Response schema for category tree."""

    data: List[CategoryTreeNode]


class CategoryReorderItem(BaseModel):
    """Single item in reorder request."""

    id: str = Field(..., description="Category ID (UUID)")
    display_order: int = Field(..., description="New display order")


class CategoryReorderRequest(BaseModel):
    """Request schema for bulk reordering categories."""

    items: List[CategoryReorderItem] = Field(..., min_length=1)
