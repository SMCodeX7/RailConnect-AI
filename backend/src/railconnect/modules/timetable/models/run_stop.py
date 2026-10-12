from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class RunStop(Base):
    __tablename__ = "run_stops"

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "stop_sequence",
            name="uq_run_stops_run_sequence",
        ),
        CheckConstraint(
            "stop_sequence > 0",
            name="positive_stop_sequence",
        ),
        CheckConstraint(
            "scheduled_arrival_at IS NOT NULL OR scheduled_departure_at IS NOT NULL",
            name="has_scheduled_time",
        ),
        CheckConstraint(
            "scheduled_arrival_at IS NULL OR scheduled_departure_at IS NULL "
            "OR scheduled_departure_at >= scheduled_arrival_at",
            name="valid_scheduled_time_order",
        ),
        CheckConstraint(
            "NOT pickup_allowed OR scheduled_departure_at IS NOT NULL",
            name="pickup_requires_departure",
        ),
        CheckConstraint(
            "NOT dropoff_allowed OR scheduled_arrival_at IS NOT NULL",
            name="dropoff_requires_arrival",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("service_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    station_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stop_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    scheduled_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pickup_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    dropoff_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
