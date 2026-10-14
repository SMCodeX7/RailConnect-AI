from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class ServiceRun(Base):
    __tablename__ = "service_runs"

    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "service_date",
            name="uq_service_runs_service_date",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'restricted')",
            name="valid_status",
        ),
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint(
            "length(trim(source_ref)) > 0",
            name="nonempty_source_ref",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    service_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("train_services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    source_ref: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
