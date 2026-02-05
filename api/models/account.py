"""Account model for managing financial accounts within budgets."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class AccountPurpose(str, enum.Enum):
    """Purpose of the account in the budget."""

    NORMAL = "normal"  # Daily finances, counted in total balance
    SAVINGS = "savings"  # Dedicated savings
    LOAN = "loan"  # Debt/installments


class AccountDatasource(str, enum.Enum):
    """Where transaction data comes from."""

    BANK = "bank"  # Normal bank account
    CREDIT = "credit"  # Credit card, can go negative
    CASH = "cash"  # Physical cash
    VIRTUAL = "virtual"  # Only exists in Tiøren


class Account(Base):
    """Account for holding transactions within a budget."""

    __tablename__ = "accounts"

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

    purpose: Mapped[AccountPurpose] = mapped_column(
        Enum(AccountPurpose, native_enum=True, name="account_purpose", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    datasource: Mapped[AccountDatasource] = mapped_column(
        Enum(AccountDatasource, native_enum=True, name="account_datasource", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="DKK",
    )

    # Starting balance (stored in øre - smallest currency unit)
    starting_balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Account rules
    can_go_negative: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    needs_coverage: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
    budget = relationship("Budget", back_populates="accounts")
    transactions = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="Transaction.date.desc()",
    )

    def __repr__(self) -> str:
        return f"<Account {self.name}>"
