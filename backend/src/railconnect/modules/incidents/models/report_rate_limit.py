from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class ReportRateLimit(Base):
    __tablename__ = "report_rate_limits"

    __table_args__ = (
        CheckConstraint(
            "key_hash ~ '^[0-9a-f]{64}$'",
            name="valid_key_hash",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="nonnegative_attempt_count",
        ),
        CheckConstraint(
            "window_expires_at > window_started_at",
            name="valid_window",
        ),
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    window_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
