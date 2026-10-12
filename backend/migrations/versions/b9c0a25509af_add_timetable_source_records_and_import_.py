"""add timetable source records and import summaries

Revision ID: b9c0a25509af
Revises: 8b4605b4bc60
Create Date: 2026-10-12 13:07:47.106994

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c0a25509af"
down_revision: str | Sequence[str] | None = "8b4605b4bc60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "source_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=False),
        sa.Column("reuse_basis", sa.Text(), nullable=False),
        sa.Column("data_kind", sa.String(length=20), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_source_records_valid_content_hash")
        ),
        sa.CheckConstraint(
            "data_kind IN ('demonstration', 'observed')",
            name=op.f("ck_source_records_valid_data_kind"),
        ),
        sa.CheckConstraint(
            "effective_until >= effective_from",
            name=op.f("ck_source_records_valid_effective_period"),
        ),
        sa.CheckConstraint(
            "length(trim(reuse_basis)) > 0", name=op.f("ck_source_records_nonempty_reuse_basis")
        ),
        sa.CheckConstraint(
            "length(trim(source_ref)) > 0", name=op.f("ck_source_records_nonempty_source_ref")
        ),
        sa.CheckConstraint(
            "length(trim(source_uri)) > 0", name=op.f("ck_source_records_nonempty_source_uri")
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0", name=op.f("ck_source_records_nonempty_title")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_records")),
        sa.UniqueConstraint("source_ref", name=op.f("uq_source_records_source_ref")),
    )
    op.create_table(
        "timetable_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("importer_version", sa.String(length=50), nullable=False),
        sa.Column("execution_context", sa.String(length=100), nullable=False),
        sa.Column("services_in_dataset", sa.Integer(), nullable=False),
        sa.Column("stops_in_dataset", sa.Integer(), nullable=False),
        sa.Column("inserted_services", sa.Integer(), nullable=False),
        sa.Column("existing_services", sa.Integer(), nullable=False),
        sa.Column("inserted_stops", sa.Integer(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "inserted_services + existing_services = services_in_dataset",
            name=op.f("ck_timetable_imports_complete_service_counts"),
        ),
        sa.CheckConstraint(
            "inserted_services >= 0 AND existing_services >= 0",
            name=op.f("ck_timetable_imports_nonnegative_service_counts"),
        ),
        sa.CheckConstraint(
            "inserted_stops >= 0 AND inserted_stops <= stops_in_dataset",
            name=op.f("ck_timetable_imports_valid_inserted_stop_count"),
        ),
        sa.CheckConstraint(
            "length(trim(execution_context)) > 0",
            name=op.f("ck_timetable_imports_nonempty_execution_context"),
        ),
        sa.CheckConstraint(
            "length(trim(importer_version)) > 0",
            name=op.f("ck_timetable_imports_nonempty_importer_version"),
        ),
        sa.CheckConstraint(
            "services_in_dataset > 0", name=op.f("ck_timetable_imports_positive_service_count")
        ),
        sa.CheckConstraint(
            "stops_in_dataset >= services_in_dataset * 2",
            name=op.f("ck_timetable_imports_valid_dataset_stop_count"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_records.id"],
            name=op.f("fk_timetable_imports_source_id_source_records"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timetable_imports")),
        sa.UniqueConstraint("source_id", name=op.f("uq_timetable_imports_source_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("timetable_imports")
    op.drop_table("source_records")
