from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'resolved')",
            name="valid_status",
        ),
        CheckConstraint(
            "version > 0",
            name="positive_version",
        ),
        CheckConstraint(
            "current_revision_number > 0",
            name="positive_current_revision",
        ),
        CheckConstraint(
            "(status = 'active' "
            "AND resolved_by_id IS NULL "
            "AND resolved_at IS NULL "
            "AND resolution_effective_at IS NULL "
            "AND resolution_reason IS NULL) OR "
            "(status = 'resolved' "
            "AND resolved_by_id IS NOT NULL "
            "AND resolved_at IS NOT NULL "
            "AND resolution_effective_at IS NOT NULL "
            "AND resolution_reason IS NOT NULL "
            "AND length(trim(resolution_reason)) BETWEEN 1 AND 2000)",
            name="consistent_resolution_state",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name="valid_resolution_record_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    originating_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("incident_reports.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    current_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_effective_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
