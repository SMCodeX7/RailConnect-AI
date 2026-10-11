from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d27ced7dc3b1"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code = upper(trim(code)) AND length(code) > 0",
            name=op.f("ck_stations_valid_code"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_stations_nonempty_name"),
        ),
        sa.CheckConstraint(
            "length(trim(source_ref)) > 0",
            name=op.f("ck_stations_nonempty_source_ref"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stations")),
        sa.UniqueConstraint("code", name=op.f("uq_stations_code")),
    )


def downgrade() -> None:
    op.drop_table("stations")
