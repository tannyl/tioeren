"""Budget model for organizing financial data."""

import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class Budget(Base):
    """Budget for organizing accounts, transactions, and financial planning."""

    __tablename__ = "budgets"

    # Primary key - UUID for security (no enumeration attacks)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Basic fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Owner relationship
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Warning threshold (stored in øre - smallest currency unit)
    warning_threshold: Mapped[int | None] = mapped_column(
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
    owner = relationship("User", back_populates="budgets", foreign_keys=[owner_id])
    accounts = relationship("Account", back_populates="budget", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="budget", cascade="all, delete-orphan")
    budget_posts = relationship("BudgetPost", back_populates="budget", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Budget {self.name}>"
