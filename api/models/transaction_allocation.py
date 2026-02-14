"""TransactionAllocation model for linking transactions to amount patterns/occurrences."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class TransactionAllocation(Base):
    """Junction table linking transactions to amount patterns or occurrences.

    Implements the split-categorization model where one transaction can be
    allocated to multiple patterns/occurrences. One allocation can be marked as 'remainder'
    to automatically receive the unallocated amount.

    Transactions bind to:
    - amount_pattern_id (FK → amount_patterns) for transactions in the active period
    - amount_occurrence_id (FK → amount_occurrences) for transactions in archived periods

    Constraint: Exactly one of amount_pattern_id or amount_occurrence_id must be set.
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

    # Amount pattern relationship (for active period transactions)
    amount_pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("amount_patterns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Amount occurrence relationship (for archived period transactions)
    amount_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("amount_occurrences.id", ondelete="CASCADE"),
        nullable=True,
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

    # Constraints and indexes
    __table_args__ = (
        # CHECK: exactly one of amount_pattern_id or amount_occurrence_id must be set
        CheckConstraint(
            "(amount_pattern_id IS NOT NULL AND amount_occurrence_id IS NULL) OR "
            "(amount_pattern_id IS NULL AND amount_occurrence_id IS NOT NULL)",
            name="ck_transaction_allocation_exactly_one_target",
        ),
        # Partial unique index: prevent duplicate allocations to same amount pattern
        Index(
            "uq_transaction_allocation_transaction_pattern",
            "transaction_id",
            "amount_pattern_id",
            unique=True,
            postgresql_where="amount_pattern_id IS NOT NULL",
        ),
        # Partial unique index: prevent duplicate allocations to same amount occurrence
        Index(
            "uq_transaction_allocation_transaction_occurrence",
            "transaction_id",
            "amount_occurrence_id",
            unique=True,
            postgresql_where="amount_occurrence_id IS NOT NULL",
        ),
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="allocations")
    amount_pattern = relationship("AmountPattern", back_populates="allocations")
    amount_occurrence = relationship("AmountOccurrence", back_populates="allocations")

    def __repr__(self) -> str:
        remainder_indicator = " (remainder)" if self.is_remainder else ""
        target_id = self.amount_pattern_id or self.amount_occurrence_id
        target_type = "pattern" if self.amount_pattern_id else "occurrence"
        return f"<TransactionAllocation {self.amount/100:.2f} kr to {target_type} {target_id}{remainder_indicator}>"
