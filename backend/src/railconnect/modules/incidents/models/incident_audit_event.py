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


class IncidentAuditEvent(Base):
    __tablename__ = "incident_audit_events"

    __table_args__ = (
        CheckConstraint(
            "action IN ('report_verified', 'report_rejected', "
            "'incident_revised', 'incident_resolved')",
            name="valid_action",
        ),
        CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 2000",
            name="valid_reason",
        ),
        CheckConstraint(
            "length(trim(request_id)) BETWEEN 1 AND 64",
            name="valid_request_id",
        ),
        CheckConstraint(
            "report_version > 0",
            name="positive_report_version",
        ),
        CheckConstraint(
            "incident_version IS NULL OR incident_version > 0",
            name="positive_incident_version",
        ),
        CheckConstraint(
            "(action = 'report_rejected' "
            "AND incident_id IS NULL "
            "AND revision_id IS NULL "
            "AND incident_version IS NULL) OR "
            "(action IN ('report_verified', 'incident_revised', 'incident_resolved') "
            "AND incident_id IS NOT NULL "
            "AND revision_id IS NOT NULL "
            "AND incident_version IS NOT NULL)",
            name="consistent_action_references",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("incident_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    revision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("incident_revisions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    report_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    incident_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
