"""Transaction model for recording financial movements on containers."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Date, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class TransactionStatus(str, enum.Enum):
    """Status of transaction categorization."""

    UNCATEGORIZED = "uncategorized"  # No rule matched, requires manual handling
    PENDING_CONFIRMATION = "pending_confirmation"  # Rule matched, needs user confirmation
    PENDING_RECEIPT = "pending_receipt"  # Requires receipt/statement before categorization
    CATEGORIZED = "categorized"  # Fully processed and assigned to budget post(s)


class Transaction(Base):
    """Transaction recording actual money movement on a container."""

    __tablename__ = "transactions"

    # Primary key - UUID for security (no enumeration attacks)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Container relationship (required - transaction must belong to a container)
    container_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction date (when it occurred, not datetime - just date)
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    # Amount in øre (smallest currency unit)
    # Positive = income, Negative = expense
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Description from bank or manual entry
    description: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # Transaction status
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=True, name="transaction_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TransactionStatus.UNCATEGORIZED,
    )

    # Internal transfer handling
    is_internal_transfer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Self-referential foreign key for internal transfers
    # Links to the counterpart transaction in the other container
    counterpart_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Bank's unique reference (if from bank import)
    # Should be unique per container (enforced at application level)
    external_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    # Hash for duplicate detection
    # Hash of: container_id + date + timestamp + amount + description
    import_hash: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
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
    # NOTE: No soft delete for transactions - they are permanent records
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
    container = relationship("Container", back_populates="transactions")
    counterpart = relationship(
        "Transaction",
        remote_side=[id],
        foreign_keys=[counterpart_transaction_id],
        uselist=False,
    )
    allocations = relationship("TransactionAllocation", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Transaction {self.date} {self.amount/100:.2f} kr - {self.description[:30]}>"
