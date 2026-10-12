from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class SourceRecord(Base):
    __tablename__ = "source_records"

    __table_args__ = (
        CheckConstraint(
            "length(trim(source_ref)) > 0",
            name="nonempty_source_ref",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="nonempty_title",
        ),
        CheckConstraint(
            "length(trim(source_uri)) > 0",
            name="nonempty_source_uri",
        ),
        CheckConstraint(
            "length(trim(reuse_basis)) > 0",
            name="nonempty_reuse_basis",
        ),
        CheckConstraint(
            "data_kind IN ('demonstration', 'observed')",
            name="valid_data_kind",
        ),
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="valid_content_hash",
        ),
        CheckConstraint(
            "effective_until >= effective_from",
            name="valid_effective_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    source_ref: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    source_uri: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    reuse_basis: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    data_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    effective_until: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
