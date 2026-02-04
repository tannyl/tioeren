"""TransactionAllocation model for linking transactions to budget posts."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class TransactionAllocation(Base):
    """Junction table linking transactions to budget posts with allocation amounts.

    Implements the split-categorization model where one transaction can be
    allocated to multiple budget posts. One allocation can be marked as 'remainder'
    to automatically receive the unallocated amount.
    """

    __tablename__ = "transaction_allocations"

    # Primary key - UUID for consistency
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Transaction relationship (required)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Budget post relationship (required)
    budget_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Allocated amount in øre (smallest currency unit)
    # For non-remainder allocations: fixed amount
    # For remainder allocation: calculated as transaction.amount - sum(other allocations)
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Marks if this allocation receives the remainder
    # Only one allocation per transaction should have is_remainder=True
    # Remainder = transaction.amount - sum(other allocations)
    is_remainder: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Timestamps (minimal audit - no created_by/updated_by for junction tables)
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

    # Unique constraint: prevent duplicate allocations to same budget post
    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "budget_post_id",
            name="uq_transaction_allocation_transaction_budget_post",
        ),
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="allocations")
    budget_post = relationship("BudgetPost", back_populates="allocations")

    def __repr__(self) -> str:
        remainder_indicator = " (remainder)" if self.is_remainder else ""
        return f"<TransactionAllocation {self.amount/100:.2f} kr to {self.budget_post_id}{remainder_indicator}>"
