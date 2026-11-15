"""Add guest-owned assistant conversations and turns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c721d8e4b305"
down_revision: str | None = "8b42c6f3a9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_conversations")),
    )
    op.create_table(
        "assistant_turns",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "turn_number > 0",
            name=op.f("ck_assistant_turns_positive_turn_number"),
        ),
        sa.CheckConstraint(
            "char_length(question) BETWEEN 1 AND 500",
            name=op.f("ck_assistant_turns_valid_question_length"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(answer) = 'object'",
            name=op.f("ck_assistant_turns_answer_is_object"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            name=op.f("fk_assistant_turns_conversation_id_assistant_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            "turn_number",
            name=op.f("pk_assistant_turns"),
        ),
    )


def downgrade() -> None:
    op.drop_table("assistant_turns")
    op.drop_table("assistant_conversations")
