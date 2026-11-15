"""Add staff attribution to timetable imports."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b42c6f3a9d1"
down_revision: str | None = "af88e86de607"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "timetable_imports",
        sa.Column("imported_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_timetable_imports_imported_by_user_id_users"),
        "timetable_imports",
        "users",
        ["imported_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_timetable_imports_imported_by_user_id_users"),
        "timetable_imports",
        type_="foreignkey",
    )
    op.drop_column("timetable_imports", "imported_by_user_id")
