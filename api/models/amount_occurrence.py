"""AmountOccurrence model for archived budget post concrete occurrences."""

import uuid
from datetime import datetime, date as date_type

from sqlalchemy import BigInteger, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.models.base import Base


class AmountOccurrence(Base):
    """Concrete amount occurrence for an archived budget post.

    Generated when a period is closed by expanding the active amount patterns
    into specific dates and amounts for that period.
    """

    __tablename__ = "amount_occurrences"

    # Primary key - UUID for consistency
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Archived budget post relationship
    archived_budget_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archived_budget_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Occurrence date (nullable for period-encompassing amounts)
    date: Mapped[date_type | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Amount in øre (smallest currency unit)
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Timestamp - immutable, only created_at
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    archived_budget_post = relationship("ArchivedBudgetPost", back_populates="amount_occurrences")

    def __repr__(self) -> str:
        date_str = self.date.isoformat() if self.date else "period"
        return f"<AmountOccurrence {self.amount} øre on {date_str}>"
