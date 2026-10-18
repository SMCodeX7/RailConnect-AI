from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class IncidentRevision(Base):
    __tablename__ = "incident_revisions"

    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "revision_number",
            name="uq_incident_revisions_incident_number",
        ),
        ForeignKeyConstraint(
            ["run_id", "departure_stop_sequence"],
            ["run_stops.run_id", "run_stops.stop_sequence"],
            name="fk_incident_revisions_departure_run_stop",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["run_id", "arrival_stop_sequence"],
            ["run_stops.run_id", "run_stops.stop_sequence"],
            name="fk_incident_revisions_arrival_run_stop",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="positive_revision_number",
        ),
        CheckConstraint(
            "scope_kind IN ('run', 'segment')",
            name="valid_scope_kind",
        ),
        CheckConstraint(
            "(scope_kind = 'run' "
            "AND departure_stop_sequence IS NULL "
            "AND arrival_stop_sequence IS NULL) OR "
            "(scope_kind = 'segment' "
            "AND departure_stop_sequence IS NOT NULL "
            "AND arrival_stop_sequence IS NOT NULL "
            "AND departure_stop_sequence > 0 "
            "AND arrival_stop_sequence > departure_stop_sequence)",
            name="consistent_scope",
        ),
        CheckConstraint(
            "impact_kind IN ('cancellation', 'restriction', 'delay')",
            name="valid_impact_kind",
        ),
        CheckConstraint(
            "impact_kind <> 'cancellation' OR scope_kind = 'run'",
            name="cancellation_requires_run_scope",
        ),
        CheckConstraint(
            "(impact_kind = 'delay' "
            "AND estimated_delay_minutes IS NOT NULL "
            "AND estimated_delay_minutes BETWEEN 1 AND 1440) OR "
            "(impact_kind IN ('cancellation', 'restriction') "
            "AND estimated_delay_minutes IS NULL)",
            name="consistent_delay",
        ),
        CheckConstraint(
            "effective_until > effective_from",
            name="valid_effective_interval",
        ),
        CheckConstraint(
            "length(trim(public_summary)) BETWEEN 1 AND 1000",
            name="valid_public_summary",
        ),
        CheckConstraint(
            "length(trim(evidence_basis)) BETWEEN 1 AND 2000",
            name="valid_evidence_basis",
        ),
        CheckConstraint(
            "length(trim(verification_reason)) BETWEEN 1 AND 2000",
            name="valid_verification_reason",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    incident_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("service_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scope_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    departure_stop_sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    arrival_stop_sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    impact_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    estimated_delay_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    effective_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    public_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_basis: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    verification_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    verified_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
