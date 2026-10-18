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


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0",
            name="nonempty_title",
        ),
        CheckConstraint(
            "length(trim(narrative)) BETWEEN 1 AND 4000",
            name="valid_narrative",
        ),
        CheckConstraint(
            "status IN ('pending', 'verified', 'rejected')",
            name="valid_status",
        ),
        CheckConstraint(
            "version > 0",
            name="positive_version",
        ),
        CheckConstraint(
            "(departure_stop_sequence_hint IS NULL "
            "AND arrival_stop_sequence_hint IS NULL) OR "
            "(run_hint_id IS NOT NULL "
            "AND departure_stop_sequence_hint IS NOT NULL "
            "AND arrival_stop_sequence_hint IS NOT NULL "
            "AND departure_stop_sequence_hint > 0 "
            "AND arrival_stop_sequence_hint > departure_stop_sequence_hint)",
            name="valid_segment_hints",
        ),
        CheckConstraint(
            "(status = 'pending' "
            "AND reviewed_by_id IS NULL "
            "AND reviewed_at IS NULL "
            "AND review_reason IS NULL) OR "
            "(status IN ('verified', 'rejected') "
            "AND reviewed_by_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL "
            "AND review_reason IS NOT NULL "
            "AND length(trim(review_reason)) BETWEEN 1 AND 2000)",
            name="consistent_review_state",
        ),
        CheckConstraint(
            "reviewed_at IS NULL OR reviewed_at >= submitted_at",
            name="valid_review_time",
        ),
        CheckConstraint(
            "submitted_by_user_id IS NULL "
            "OR reviewed_by_id IS NULL "
            "OR submitted_by_user_id <> reviewed_by_id",
            name="no_staff_self_review",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )
    narrative: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    run_hint_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("service_runs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    station_hint_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    departure_stop_sequence_hint: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    arrival_stop_sequence_hint: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
