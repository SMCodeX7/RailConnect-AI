"""add staff identity sessions and login limits

Revision ID: dfeb4f1c64a4
Revises: b9c0a25509af
Create Date: 2026-10-12 16:18:34.746291

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfeb4f1c64a4"
down_revision: str | Sequence[str] | None = "b9c0a25509af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "login_rate_limits",
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "key_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_login_rate_limits_valid_key_hash")
        ),
        sa.CheckConstraint(
            "scope IN ('client', 'account')", name=op.f("ck_login_rate_limits_valid_scope")
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name=op.f("ck_login_rate_limits_nonnegative_attempt_count")
        ),
        sa.CheckConstraint(
            "window_expires_at > window_started_at", name=op.f("ck_login_rate_limits_valid_window")
        ),
        sa.PrimaryKeyConstraint("scope", "key_hash", name=op.f("pk_login_rate_limits")),
    )
    op.create_index(
        op.f("ix_login_rate_limits_window_expires_at"),
        "login_rate_limits",
        ["window_expires_at"],
        unique=False,
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("code ~ '^[a-z][a-z0-9_]{1,39}$'", name=op.f("ck_roles_valid_code")),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0", name=op.f("ck_roles_nonempty_display_name")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("auth_version", sa.Integer(), server_default="1", nullable=False),
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
            "username ~ '^[a-z][a-z0-9_.-]{2,63}$'", name=op.f("ck_users_valid_username")
        ),
        sa.CheckConstraint("auth_version > 0", name=op.f("ck_users_positive_auth_version")),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0", name=op.f("ck_users_nonempty_display_name")
        ),
        sa.CheckConstraint(
            "length(trim(password_hash)) > 0", name=op.f("ck_users_nonempty_password_hash")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "csrf_token ~ '^[0-9a-f]{64}$'", name=op.f("ck_sessions_valid_csrf_token")
        ),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_sessions_valid_token_hash")
        ),
        sa.CheckConstraint("auth_version > 0", name=op.f("ck_sessions_positive_auth_version")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_sessions_valid_expiry")),
        sa.CheckConstraint(
            "last_seen_at >= created_at AND last_seen_at < expires_at",
            name=op.f("ck_sessions_valid_last_seen"),
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name=op.f("ck_sessions_valid_revocation_time"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_roles_role_id"), table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_index(op.f("ix_login_rate_limits_window_expires_at"), table_name="login_rate_limits")
    op.drop_table("login_rate_limits")
