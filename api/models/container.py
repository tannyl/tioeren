"""Container model for managing financial containers within budgets."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Enum, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class ContainerType(str, enum.Enum):
    """Type of the container in the budget."""

    CASHBOX = "cashbox"  # Daily finances (checking account, cash, etc.)
    PIGGYBANK = "piggybank"  # Dedicated savings
    DEBT = "debt"  # Loans, credit cards, mortgages


class Container(Base):
    """Container for holding transactions within a budget."""

    __tablename__ = "containers"

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

    # Basic fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    type: Mapped[ContainerType] = mapped_column(
        Enum(ContainerType, native_enum=True, name="container_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Starting balance (stored in øre - smallest currency unit)
    starting_balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Bank metadata (optional for all types)
    bank_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    bank_account_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    bank_reg_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    bank_account_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Cashbox-specific fields
    overdraft_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
    )

    # Piggybank-specific fields
    locked: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
    )

    # Debt-specific fields
    credit_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
    )

    allow_withdrawals: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
    )

    interest_rate: Mapped[float | None] = mapped_column(
        Numeric,
        nullable=True,
        default=None,
    )

    interest_frequency: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    required_payment: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
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
    budget = relationship("Budget", back_populates="containers")
    transactions = relationship(
        "Transaction",
        back_populates="container",
        cascade="all, delete-orphan",
        order_by="Transaction.date.desc()",
    )

    def __repr__(self) -> str:
        return f"<Container {self.name}>"
