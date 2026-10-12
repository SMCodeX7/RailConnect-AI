"""Add dated service runs and stop permissions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b4605b4bc60"
down_revision: str | Sequence[str] | None = "cbaf28463dbe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'restricted')",
            name=op.f("ck_service_runs_valid_status"),
        ),
        sa.CheckConstraint(
            "length(trim(source_ref)) > 0",
            name=op.f("ck_service_runs_nonempty_source_ref"),
        ),
        sa.CheckConstraint(
            "version > 0",
            name=op.f("ck_service_runs_positive_version"),
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["train_services.id"],
            name=op.f("fk_service_runs_service_id_train_services"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_service_runs"),
        ),
        sa.UniqueConstraint(
            "service_id",
            "service_date",
            name="uq_service_runs_service_date",
        ),
    )
    op.create_index(
        op.f("ix_service_runs_service_date"),
        "service_runs",
        ["service_date"],
        unique=False,
    )

    op.create_table(
        "run_stops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("station_id", sa.Uuid(), nullable=False),
        sa.Column("stop_sequence", sa.Integer(), nullable=False),
        sa.Column(
            "scheduled_arrival_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "scheduled_departure_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "pickup_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "dropoff_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "NOT dropoff_allowed OR scheduled_arrival_at IS NOT NULL",
            name=op.f("ck_run_stops_dropoff_requires_arrival"),
        ),
        sa.CheckConstraint(
            "NOT pickup_allowed OR scheduled_departure_at IS NOT NULL",
            name=op.f("ck_run_stops_pickup_requires_departure"),
        ),
        sa.CheckConstraint(
            "scheduled_arrival_at IS NOT NULL OR scheduled_departure_at IS NOT NULL",
            name=op.f("ck_run_stops_has_scheduled_time"),
        ),
        sa.CheckConstraint(
            "scheduled_arrival_at IS NULL OR scheduled_departure_at IS NULL "
            "OR scheduled_departure_at >= scheduled_arrival_at",
            name=op.f("ck_run_stops_valid_scheduled_time_order"),
        ),
        sa.CheckConstraint(
            "stop_sequence > 0",
            name=op.f("ck_run_stops_positive_stop_sequence"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["service_runs.id"],
            name=op.f("fk_run_stops_run_id_service_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            name=op.f("fk_run_stops_station_id_stations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_run_stops"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "stop_sequence",
            name="uq_run_stops_run_sequence",
        ),
    )
    op.create_index(
        op.f("ix_run_stops_station_id"),
        "run_stops",
        ["station_id"],
        unique=False,
    )

    op.add_column(
        "service_stops",
        sa.Column(
            "pickup_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "service_stops",
        sa.Column(
            "dropoff_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE service_stops
            SET pickup_allowed = departure_minutes IS NOT NULL,
                dropoff_allowed = arrival_minutes IS NOT NULL
            WHERE service_id IN (
                SELECT id
                FROM train_services
                WHERE source_ref = 'demo-timetable-v1'
            )
            """
        )
    )

    op.create_check_constraint(
        op.f("ck_service_stops_pickup_requires_departure"),
        "service_stops",
        "NOT pickup_allowed OR departure_minutes IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_service_stops_dropoff_requires_arrival"),
        "service_stops",
        "NOT dropoff_allowed OR arrival_minutes IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_service_stops_dropoff_requires_arrival"),
        "service_stops",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_service_stops_pickup_requires_departure"),
        "service_stops",
        type_="check",
    )
    op.drop_column("service_stops", "dropoff_allowed")
    op.drop_column("service_stops", "pickup_allowed")

    op.drop_index(
        op.f("ix_run_stops_station_id"),
        table_name="run_stops",
    )
    op.drop_table("run_stops")
    op.drop_index(
        op.f("ix_service_runs_service_date"),
        table_name="service_runs",
    )
    op.drop_table("service_runs")
