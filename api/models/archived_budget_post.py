"""ArchivedBudgetPost model for period-specific budget snapshots."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Enum, Integer, Index, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base
from api.models.budget_post import BudgetPostDirection, BudgetPostType


class ArchivedBudgetPost(Base):
    """Archived budget post representing a snapshot of expectations for a specific period.

    Created when a period is closed. Immutable snapshot of what was expected
    in that period, with concrete amount occurrences instead of patterns.
    """

    __tablename__ = "archived_budget_posts"
    __table_args__ = (
        # Only one archived budget post per category path per period
        Index(
            'uq_archived_budget_post_category_path_period',
            'budget_id',
            'direction',
            'category_path',
            'period_year',
            'period_month',
            unique=True,
            postgresql_where='category_path IS NOT NULL',
        ),
    )

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

    # Reference to the active budget post (nullable - can be deleted)
    budget_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Period identification
    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Snapshot of budget post properties
    direction: Mapped[BudgetPostDirection] = mapped_column(
        Enum(BudgetPostDirection, native_enum=True, name="budget_post_direction", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Category path - nullable (null for transfers)
    # Full path including name as last element, e.g., ["Bolig", "Husleje"]
    category_path: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )

    # Display order matching category_path levels for sorting
    display_order: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )

    type: Mapped[BudgetPostType] = mapped_column(
        Enum(BudgetPostType, native_enum=True, name="budget_post_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Timestamps - immutable, only created_at and created_by
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Audit trail - who created
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    budget = relationship("Budget", back_populates="archived_budget_posts")
    budget_post = relationship("BudgetPost")
    amount_occurrences = relationship("AmountOccurrence", back_populates="archived_budget_post", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        if self.category_path:
            return f"<ArchivedBudgetPost {self.category_path[-1]} {self.period_year}-{self.period_month:02d} ({self.type.value})>"
        else:
            return f"<ArchivedBudgetPost transfer {self.period_year}-{self.period_month:02d} ({self.type.value})>"
