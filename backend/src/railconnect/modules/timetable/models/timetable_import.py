from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class TimetableImport(Base):
    __tablename__ = "timetable_imports"

    __table_args__ = (
        CheckConstraint(
            "services_in_dataset > 0",
            name="positive_service_count",
        ),
        CheckConstraint(
            "stops_in_dataset >= services_in_dataset * 2",
            name="valid_dataset_stop_count",
        ),
        CheckConstraint(
            "inserted_services >= 0 AND existing_services >= 0",
            name="nonnegative_service_counts",
        ),
        CheckConstraint(
            "inserted_services + existing_services = services_in_dataset",
            name="complete_service_counts",
        ),
        CheckConstraint(
            "inserted_stops >= 0 AND inserted_stops <= stops_in_dataset",
            name="valid_inserted_stop_count",
        ),
        CheckConstraint(
            "length(trim(importer_version)) > 0",
            name="nonempty_importer_version",
        ),
        CheckConstraint(
            "length(trim(execution_context)) > 0",
            name="nonempty_execution_context",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    importer_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    execution_context: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    services_in_dataset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    stops_in_dataset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    inserted_services: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    existing_services: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    inserted_stops: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
