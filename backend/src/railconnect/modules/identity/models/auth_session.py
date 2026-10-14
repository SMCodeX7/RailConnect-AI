from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class AuthSession(Base):
    __tablename__ = "sessions"

    __table_args__ = (
        CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name="valid_token_hash",
        ),
        CheckConstraint(
            "csrf_token ~ '^[0-9a-f]{64}$'",
            name="valid_csrf_token",
        ),
        CheckConstraint(
            "auth_version > 0",
            name="positive_auth_version",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="valid_expiry",
        ),
        CheckConstraint(
            "last_seen_at >= created_at AND last_seen_at < expires_at",
            name="valid_last_seen",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="valid_revocation_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
