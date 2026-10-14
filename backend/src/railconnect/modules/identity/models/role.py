from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9_]{1,39}$'",
            name="valid_code",
        ),
        CheckConstraint(
            "length(trim(display_name)) > 0",
            name="nonempty_display_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
