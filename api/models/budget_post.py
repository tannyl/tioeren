"""BudgetPost model for planned/expected transactions within a budget."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class BudgetPostType(str, enum.Enum):
    """Type of budget post determining how the amount is handled."""

    FIXED = "fixed"  # Precise amount each period (e.g., rent, salary)
    CEILING = "ceiling"  # Maximum amount per period (e.g., groceries, entertainment)
    ROLLING = "rolling"  # Accumulates over time (e.g., car repair fund)


class BudgetPost(Base):
    """Budget post representing planned/expected transactions within a budget."""

    __tablename__ = "budget_posts"

    # Primary key - UUID for security (no enumeration attacks)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Budget relationship
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category relationship
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    type: Mapped[BudgetPostType] = mapped_column(
        Enum(BudgetPostType, native_enum=True, name="budget_post_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Amount in øre (smallest currency unit)
    # amount_min: minimum expected amount (or fixed amount for FIXED type)
    amount_min: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # amount_max: maximum expected amount (only used for CEILING type, nullable otherwise)
    amount_max: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Account bindings stored as JSON arrays of UUIDs
    # from_account_ids: which accounts can be the source (for expenses/transfers)
    # to_account_ids: which accounts can be the destination (for income/transfers)
    # Both can be NULL (meaning not applicable), or JSON arrays of account UUIDs
    from_account_ids: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    to_account_ids: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Recurrence pattern stored as JSON
    # Contains configuration for how often and when this budget post occurs
    # Structure TBD based on recurrence requirements from spec
    recurrence_pattern: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Audit trail - who created/updated
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    budget = relationship("Budget", back_populates="budget_posts")
    category = relationship("Category", back_populates="budget_posts")
    allocations = relationship("TransactionAllocation", back_populates="budget_post", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BudgetPost {self.name} ({self.type.value})>"
