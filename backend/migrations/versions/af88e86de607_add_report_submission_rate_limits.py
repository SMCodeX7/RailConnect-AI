"""Add report submission rate limits.

Revision ID: af88e86de607
Revises: 5c23c99becea
Create Date: 2026-10-14 21:24:38.342080
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "af88e86de607"
down_revision: str | Sequence[str] | None = "5c23c99becea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create separate report-submission counters."""
    op.create_table(
        "report_rate_limits",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "window_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "key_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_report_rate_limits_valid_key_hash"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_report_rate_limits_nonnegative_attempt_count"),
        ),
        sa.CheckConstraint(
            "window_expires_at > window_started_at",
            name=op.f("ck_report_rate_limits_valid_window"),
        ),
        sa.PrimaryKeyConstraint(
            "key_hash",
            name=op.f("pk_report_rate_limits"),
        ),
    )
    op.create_index(
        op.f("ix_report_rate_limits_window_expires_at"),
        "report_rate_limits",
        ["window_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove report-submission counters."""
    op.drop_index(
        op.f("ix_report_rate_limits_window_expires_at"),
        table_name="report_rate_limits",
    )
    op.drop_table("report_rate_limits")
