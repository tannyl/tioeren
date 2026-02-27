"""AmountPattern model for budget post amount and recurrence variations."""

import uuid
from datetime import datetime, date as date_type

from sqlalchemy import String, BigInteger, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class AmountPattern(Base):
    """Amount pattern for budget posts, allowing multiple patterns per post."""

    __tablename__ = "amount_patterns"

    # Primary key - UUID for security (no enumeration attacks)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Budget post relationship
    budget_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount in øre (smallest currency unit)
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Date range when this pattern is active
    start_date: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date_type | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Recurrence pattern stored as JSON
    # Contains configuration for how often and when this amount occurs
    recurrence_pattern: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Container IDs for this pattern stored as JSON array of UUID strings
    # Income/Expense: MUST be non-empty subset of budget post's container pool
    # Transfer: MUST be null
    container_ids: Mapped[list | None] = mapped_column(
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
    budget_post = relationship("BudgetPost", back_populates="amount_patterns")
    allocations = relationship("TransactionAllocation", back_populates="amount_pattern", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AmountPattern {self.amount} øre from {self.start_date}>"
