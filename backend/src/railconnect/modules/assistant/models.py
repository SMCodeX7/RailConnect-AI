from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from railconnect.db.base import Base


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AssistantTurn(Base):
    __tablename__ = "assistant_turns"
    __table_args__ = (
        CheckConstraint("turn_number > 0", name="positive_turn_number"),
        CheckConstraint("char_length(question) BETWEEN 1 AND 500", name="valid_question_length"),
        CheckConstraint("jsonb_typeof(answer) = 'object'", name="answer_is_object"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    turn_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
