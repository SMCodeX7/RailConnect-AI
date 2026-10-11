from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Integer, String, Uuid, func, true
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class TrainService(Base):
    __tablename__ = "train_services"
    __table_args__ = (
        CheckConstraint(
            "code = upper(trim(code)) AND length(code) > 0",
            name="valid_code",
        ),
        CheckConstraint("length(trim(name)) > 0", name="nonempty_name"),
        CheckConstraint(
            "length(trim(source_ref)) > 0",
            name="nonempty_source_ref",
        ),
        CheckConstraint(
            "operating_days BETWEEN 1 AND 127",
            name="valid_operating_days",
        ),
        CheckConstraint(
            "valid_until >= valid_from",
            name="valid_date_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    operating_days: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
