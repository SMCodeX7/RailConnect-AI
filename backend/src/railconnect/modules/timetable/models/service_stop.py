from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class ServiceStop(Base):
    __tablename__ = "service_stops"
    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "stop_sequence",
            name="uq_service_stops_service_sequence",
        ),
        CheckConstraint("stop_sequence > 0", name="positive_stop_sequence"),
        CheckConstraint(
            "arrival_minutes IS NOT NULL OR departure_minutes IS NOT NULL",
            name="has_stop_time",
        ),
        CheckConstraint(
            "arrival_minutes IS NULL OR arrival_minutes BETWEEN 0 AND 4319",
            name="valid_arrival_minutes",
        ),
        CheckConstraint(
            "departure_minutes IS NULL OR departure_minutes BETWEEN 0 AND 4319",
            name="valid_departure_minutes",
        ),
        CheckConstraint(
            "arrival_minutes IS NULL OR departure_minutes IS NULL "
            "OR departure_minutes >= arrival_minutes",
            name="valid_stop_time_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("train_services.id", ondelete="CASCADE"),
        nullable=False,
    )
    station_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    departure_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
