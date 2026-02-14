"""BudgetPost model for planned/expected transactions within a budget."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, ForeignKey, DateTime, Enum, Integer, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class BudgetPostDirection(str, enum.Enum):
    """Direction of money flow for a budget post."""

    INCOME = "income"  # Money coming in
    EXPENSE = "expense"  # Money going out
    TRANSFER = "transfer"  # Money moving between accounts


class CounterpartyType(str, enum.Enum):
    """Type of counterparty for income/expense budget posts."""

    EXTERNAL = "external"  # External entity (employer, store, etc.)
    ACCOUNT = "account"  # Another account in the system (savings/loan)


class BudgetPostType(str, enum.Enum):
    """Type of budget post determining how the amount is handled."""

    FIXED = "fixed"  # Precise amount each period (e.g., rent, salary)
    CEILING = "ceiling"  # Maximum amount per period (e.g., groceries, entertainment)


class BudgetPost(Base):
    """Active budget post representing current/future planned transactions.

    Represents what we expect to happen NOW and forward. No period - one active
    budget post per category. Archived snapshots are stored in ArchivedBudgetPost.
    """

    __tablename__ = "budget_posts"
    __table_args__ = (
        # Only one active budget post per category (where category_id is not null and not deleted)
        Index(
            'uq_budget_post_category',
            'category_id',
            unique=True,
            postgresql_where='category_id IS NOT NULL AND deleted_at IS NULL',
        ),
        # Only one active transfer between same account pair (not deleted)
        Index(
            'uq_budget_post_transfer_accounts',
            'transfer_from_account_id',
            'transfer_to_account_id',
            unique=True,
            postgresql_where="direction = 'transfer' AND deleted_at IS NULL",
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

    # Direction: income, expense, or transfer
    direction: Mapped[BudgetPostDirection] = mapped_column(
        Enum(BudgetPostDirection, native_enum=True, name="budget_post_direction", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Category relationship - nullable (null for transfers)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Basic fields
    type: Mapped[BudgetPostType] = mapped_column(
        Enum(BudgetPostType, native_enum=True, name="budget_post_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Accumulate flag - only for ceiling type
    accumulate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Counterparty for income/expense (null for transfers)
    counterparty_type: Mapped[CounterpartyType | None] = mapped_column(
        Enum(CounterpartyType, native_enum=True, name="counterparty_type", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Counterparty account (only if counterparty_type = 'account')
    counterparty_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Transfer accounts (only for direction = 'transfer')
    transfer_from_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    transfer_to_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
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
    amount_patterns = relationship("AmountPattern", back_populates="budget_post", cascade="all, delete-orphan")
    counterparty_account = relationship("Account", foreign_keys=[counterparty_account_id])
    transfer_from_account = relationship("Account", foreign_keys=[transfer_from_account_id])
    transfer_to_account = relationship("Account", foreign_keys=[transfer_to_account_id])

    def __repr__(self) -> str:
        if self.category:
            return f"<BudgetPost {self.category.name} ({self.direction.value}, {self.type.value})>"
        else:
            return f"<BudgetPost transfer ({self.type.value})>"
