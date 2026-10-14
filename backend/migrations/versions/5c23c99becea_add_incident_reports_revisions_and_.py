"""Add incident reports, revisions and audit events.

Revision ID: 5c23c99becea
Revises: dfeb4f1c64a4
Create Date: 2026-10-14 20:42:55.386101
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c23c99becea"
down_revision: str | Sequence[str] | None = "dfeb4f1c64a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create incident records and protect immutable history."""
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("run_hint_id", sa.Uuid(), nullable=True),
        sa.Column("station_hint_id", sa.Uuid(), nullable=True),
        sa.Column("departure_stop_sequence_hint", sa.Integer(), nullable=True),
        sa.Column("arrival_stop_sequence_hint", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(status = 'pending' "
            "AND reviewed_by_id IS NULL "
            "AND reviewed_at IS NULL "
            "AND review_reason IS NULL) OR "
            "(status IN ('verified', 'rejected') "
            "AND reviewed_by_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL "
            "AND review_reason IS NOT NULL "
            "AND length(trim(review_reason)) BETWEEN 1 AND 2000)",
            name=op.f("ck_incident_reports_consistent_review_state"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'verified', 'rejected')",
            name=op.f("ck_incident_reports_valid_status"),
        ),
        sa.CheckConstraint(
            "(departure_stop_sequence_hint IS NULL "
            "AND arrival_stop_sequence_hint IS NULL) OR "
            "(run_hint_id IS NOT NULL "
            "AND departure_stop_sequence_hint IS NOT NULL "
            "AND arrival_stop_sequence_hint IS NOT NULL "
            "AND departure_stop_sequence_hint > 0 "
            "AND arrival_stop_sequence_hint > departure_stop_sequence_hint)",
            name=op.f("ck_incident_reports_valid_segment_hints"),
        ),
        sa.CheckConstraint(
            "length(trim(narrative)) BETWEEN 1 AND 4000",
            name=op.f("ck_incident_reports_valid_narrative"),
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name=op.f("ck_incident_reports_nonempty_title"),
        ),
        sa.CheckConstraint(
            "reviewed_at IS NULL OR reviewed_at >= submitted_at",
            name=op.f("ck_incident_reports_valid_review_time"),
        ),
        sa.CheckConstraint(
            "submitted_by_user_id IS NULL "
            "OR reviewed_by_id IS NULL "
            "OR submitted_by_user_id <> reviewed_by_id",
            name=op.f("ck_incident_reports_no_staff_self_review"),
        ),
        sa.CheckConstraint(
            "version > 0",
            name=op.f("ck_incident_reports_positive_version"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
            name=op.f("fk_incident_reports_reviewed_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_hint_id"],
            ["service_runs.id"],
            name=op.f("fk_incident_reports_run_hint_id_service_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["station_hint_id"],
            ["stations.id"],
            name=op.f("fk_incident_reports_station_hint_id_stations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name=op.f("fk_incident_reports_submitted_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_reports")),
    )

    op.create_index(
        op.f("ix_incident_reports_reviewed_by_id"),
        "incident_reports",
        ["reviewed_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_run_hint_id"),
        "incident_reports",
        ["run_hint_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_station_hint_id"),
        "incident_reports",
        ["station_hint_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_status"),
        "incident_reports",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_submitted_by_user_id"),
        "incident_reports",
        ["submitted_by_user_id"],
        unique=False,
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("originating_report_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "current_revision_number",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolution_effective_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(status = 'active' "
            "AND resolved_by_id IS NULL "
            "AND resolved_at IS NULL "
            "AND resolution_effective_at IS NULL "
            "AND resolution_reason IS NULL) OR "
            "(status = 'resolved' "
            "AND resolved_by_id IS NOT NULL "
            "AND resolved_at IS NOT NULL "
            "AND resolution_effective_at IS NOT NULL "
            "AND resolution_reason IS NOT NULL "
            "AND length(trim(resolution_reason)) BETWEEN 1 AND 2000)",
            name=op.f("ck_incidents_consistent_resolution_state"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'resolved')",
            name=op.f("ck_incidents_valid_status"),
        ),
        sa.CheckConstraint(
            "current_revision_number > 0",
            name=op.f("ck_incidents_positive_current_revision"),
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name=op.f("ck_incidents_valid_resolution_record_time"),
        ),
        sa.CheckConstraint(
            "version > 0",
            name=op.f("ck_incidents_positive_version"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_incidents_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["originating_report_id"],
            ["incident_reports.id"],
            name=op.f("fk_incidents_originating_report_id_incident_reports"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_incidents_resolved_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint(
            "originating_report_id",
            name=op.f("uq_incidents_originating_report_id"),
        ),
    )

    op.create_index(
        op.f("ix_incidents_created_by_id"),
        "incidents",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incidents_resolved_by_id"),
        "incidents",
        ["resolved_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incidents_status"),
        "incidents",
        ["status"],
        unique=False,
    )

    op.create_table(
        "incident_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("scope_kind", sa.String(length=20), nullable=False),
        sa.Column("departure_stop_sequence", sa.Integer(), nullable=True),
        sa.Column("arrival_stop_sequence", sa.Integer(), nullable=True),
        sa.Column("impact_kind", sa.String(length=20), nullable=False),
        sa.Column("estimated_delay_minutes", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_summary", sa.Text(), nullable=False),
        sa.Column("evidence_basis", sa.Text(), nullable=False),
        sa.Column("verification_reason", sa.Text(), nullable=False),
        sa.Column("verified_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(impact_kind = 'delay' "
            "AND estimated_delay_minutes IS NOT NULL "
            "AND estimated_delay_minutes BETWEEN 1 AND 1440) OR "
            "(impact_kind IN ('cancellation', 'restriction') "
            "AND estimated_delay_minutes IS NULL)",
            name=op.f("ck_incident_revisions_consistent_delay"),
        ),
        sa.CheckConstraint(
            "(scope_kind = 'run' "
            "AND departure_stop_sequence IS NULL "
            "AND arrival_stop_sequence IS NULL) OR "
            "(scope_kind = 'segment' "
            "AND departure_stop_sequence IS NOT NULL "
            "AND arrival_stop_sequence IS NOT NULL "
            "AND departure_stop_sequence > 0 "
            "AND arrival_stop_sequence > departure_stop_sequence)",
            name=op.f("ck_incident_revisions_consistent_scope"),
        ),
        sa.CheckConstraint(
            "impact_kind <> 'cancellation' OR scope_kind = 'run'",
            name=op.f("ck_incident_revisions_cancellation_requires_run_scope"),
        ),
        sa.CheckConstraint(
            "impact_kind IN ('cancellation', 'restriction', 'delay')",
            name=op.f("ck_incident_revisions_valid_impact_kind"),
        ),
        sa.CheckConstraint(
            "scope_kind IN ('run', 'segment')",
            name=op.f("ck_incident_revisions_valid_scope_kind"),
        ),
        sa.CheckConstraint(
            "effective_until > effective_from",
            name=op.f("ck_incident_revisions_valid_effective_interval"),
        ),
        sa.CheckConstraint(
            "length(trim(evidence_basis)) BETWEEN 1 AND 2000",
            name=op.f("ck_incident_revisions_valid_evidence_basis"),
        ),
        sa.CheckConstraint(
            "length(trim(public_summary)) BETWEEN 1 AND 1000",
            name=op.f("ck_incident_revisions_valid_public_summary"),
        ),
        sa.CheckConstraint(
            "length(trim(verification_reason)) BETWEEN 1 AND 2000",
            name=op.f("ck_incident_revisions_valid_verification_reason"),
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name=op.f("ck_incident_revisions_positive_revision_number"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_revisions_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "arrival_stop_sequence"],
            ["run_stops.run_id", "run_stops.stop_sequence"],
            name="fk_incident_revisions_arrival_run_stop",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "departure_stop_sequence"],
            ["run_stops.run_id", "run_stops.stop_sequence"],
            name="fk_incident_revisions_departure_run_stop",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["service_runs.id"],
            name=op.f("fk_incident_revisions_run_id_service_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by_id"],
            ["users.id"],
            name=op.f("fk_incident_revisions_verified_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_revisions")),
        sa.UniqueConstraint(
            "incident_id",
            "revision_number",
            name="uq_incident_revisions_incident_number",
        ),
    )

    op.create_index(
        op.f("ix_incident_revisions_effective_from"),
        "incident_revisions",
        ["effective_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_revisions_run_id"),
        "incident_revisions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_revisions_verified_by_id"),
        "incident_revisions",
        ["verified_by_id"],
        unique=False,
    )

    op.create_table(
        "incident_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("report_version", sa.Integer(), nullable=False),
        sa.Column("incident_version", sa.Integer(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(action = 'report_rejected' "
            "AND incident_id IS NULL "
            "AND revision_id IS NULL "
            "AND incident_version IS NULL) OR "
            "(action IN ('report_verified', 'incident_revised', 'incident_resolved') "
            "AND incident_id IS NOT NULL "
            "AND revision_id IS NOT NULL "
            "AND incident_version IS NOT NULL)",
            name=op.f("ck_incident_audit_events_consistent_action_references"),
        ),
        sa.CheckConstraint(
            "action IN ('report_verified', 'report_rejected', "
            "'incident_revised', 'incident_resolved')",
            name=op.f("ck_incident_audit_events_valid_action"),
        ),
        sa.CheckConstraint(
            "incident_version IS NULL OR incident_version > 0",
            name=op.f("ck_incident_audit_events_positive_incident_version"),
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 2000",
            name=op.f("ck_incident_audit_events_valid_reason"),
        ),
        sa.CheckConstraint(
            "length(trim(request_id)) BETWEEN 1 AND 64",
            name=op.f("ck_incident_audit_events_valid_request_id"),
        ),
        sa.CheckConstraint(
            "report_version > 0",
            name=op.f("ck_incident_audit_events_positive_report_version"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_incident_audit_events_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_audit_events_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["incident_reports.id"],
            name=op.f("fk_incident_audit_events_report_id_incident_reports"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["incident_revisions.id"],
            name=op.f("fk_incident_audit_events_revision_id_incident_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_audit_events")),
    )

    op.create_index(
        op.f("ix_incident_audit_events_actor_id"),
        "incident_audit_events",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_audit_events_incident_id"),
        "incident_audit_events",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_audit_events_occurred_at"),
        "incident_audit_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_audit_events_report_id"),
        "incident_audit_events",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_audit_events_request_id"),
        "incident_audit_events",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_audit_events_revision_id"),
        "incident_audit_events",
        ["revision_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION railconnect_reject_incident_history_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION USING
                ERRCODE = '55000',
                MESSAGE = format('%I is append-only', TG_TABLE_NAME);
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER incident_revisions_reject_mutation
        BEFORE UPDATE OR DELETE ON incident_revisions
        FOR EACH ROW
        EXECUTE FUNCTION railconnect_reject_incident_history_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER incident_revisions_reject_truncate
        BEFORE TRUNCATE ON incident_revisions
        FOR EACH STATEMENT
        EXECUTE FUNCTION railconnect_reject_incident_history_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER incident_audit_events_reject_mutation
        BEFORE UPDATE OR DELETE ON incident_audit_events
        FOR EACH ROW
        EXECUTE FUNCTION railconnect_reject_incident_history_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER incident_audit_events_reject_truncate
        BEFORE TRUNCATE ON incident_audit_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION railconnect_reject_incident_history_mutation();
        """
    )


def downgrade() -> None:
    """Remove history protections and incident tables."""
    op.execute("DROP TRIGGER incident_audit_events_reject_truncate ON incident_audit_events")
    op.execute("DROP TRIGGER incident_audit_events_reject_mutation ON incident_audit_events")
    op.execute("DROP TRIGGER incident_revisions_reject_truncate ON incident_revisions")
    op.execute("DROP TRIGGER incident_revisions_reject_mutation ON incident_revisions")
    op.execute("DROP FUNCTION railconnect_reject_incident_history_mutation()")

    op.drop_index(
        op.f("ix_incident_audit_events_revision_id"),
        table_name="incident_audit_events",
    )
    op.drop_index(
        op.f("ix_incident_audit_events_request_id"),
        table_name="incident_audit_events",
    )
    op.drop_index(
        op.f("ix_incident_audit_events_report_id"),
        table_name="incident_audit_events",
    )
    op.drop_index(
        op.f("ix_incident_audit_events_occurred_at"),
        table_name="incident_audit_events",
    )
    op.drop_index(
        op.f("ix_incident_audit_events_incident_id"),
        table_name="incident_audit_events",
    )
    op.drop_index(
        op.f("ix_incident_audit_events_actor_id"),
        table_name="incident_audit_events",
    )
    op.drop_table("incident_audit_events")

    op.drop_index(
        op.f("ix_incident_revisions_verified_by_id"),
        table_name="incident_revisions",
    )
    op.drop_index(
        op.f("ix_incident_revisions_run_id"),
        table_name="incident_revisions",
    )
    op.drop_index(
        op.f("ix_incident_revisions_effective_from"),
        table_name="incident_revisions",
    )
    op.drop_table("incident_revisions")

    op.drop_index(
        op.f("ix_incidents_status"),
        table_name="incidents",
    )
    op.drop_index(
        op.f("ix_incidents_resolved_by_id"),
        table_name="incidents",
    )
    op.drop_index(
        op.f("ix_incidents_created_by_id"),
        table_name="incidents",
    )
    op.drop_table("incidents")

    op.drop_index(
        op.f("ix_incident_reports_submitted_by_user_id"),
        table_name="incident_reports",
    )
    op.drop_index(
        op.f("ix_incident_reports_status"),
        table_name="incident_reports",
    )
    op.drop_index(
        op.f("ix_incident_reports_station_hint_id"),
        table_name="incident_reports",
    )
    op.drop_index(
        op.f("ix_incident_reports_run_hint_id"),
        table_name="incident_reports",
    )
    op.drop_index(
        op.f("ix_incident_reports_reviewed_by_id"),
        table_name="incident_reports",
    )
    op.drop_table("incident_reports")
