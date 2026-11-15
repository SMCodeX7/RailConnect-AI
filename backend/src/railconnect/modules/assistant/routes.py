import re
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.db.dependencies import DatabaseSession
from railconnect.modules.assistant.answer_schemas import AssistantAnswer, AssistantQuestion
from railconnect.modules.assistant.answer_service import answer_policy_question
from railconnect.modules.assistant.models import AssistantConversation, AssistantTurn
from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    IdentitySettings,
    validate_request_origin,
)

router = APIRouter(prefix="/assistant/conversations", tags=["Passenger assistant"])

OWNER_COOKIE = "railconnect_assistant_owner"
OWNER_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
MAX_TURNS = 30


class ConversationCreated(BaseModel):
    conversation_id: UUID


class ConversationTurn(BaseModel):
    turn_number: int
    question: str
    answer: AssistantAnswer


class ConversationHistory(BaseModel):
    conversation_id: UUID
    turns: list[ConversationTurn]


def _token_hash(token: str) -> str:
    return sha256(token.encode("ascii")).hexdigest()


def _require_owner(
    session: Session,
    conversation_id: UUID,
    token: str | None,
    *,
    lock: bool = False,
) -> None:
    if token is None or OWNER_TOKEN_PATTERN.fullmatch(token) is None:
        raise HTTPException(status_code=404, headers=NO_STORE_HEADERS)

    statement = select(AssistantConversation.id).where(
        AssistantConversation.id == conversation_id,
        AssistantConversation.owner_token_hash == _token_hash(token),
    )
    if lock:
        statement = statement.with_for_update()

    if session.scalar(statement) is None:
        raise HTTPException(status_code=404, headers=NO_STORE_HEADERS)


@router.post("", response_model=ConversationCreated, status_code=201)
def create_conversation(
    request: Request,
    response: Response,
    session: DatabaseSession,
    settings: IdentitySettings,
) -> ConversationCreated:
    validate_request_origin(request, settings)
    token = token_urlsafe(32)

    with session.begin():
        conversation = AssistantConversation(owner_token_hash=_token_hash(token))
        session.add(conversation)
        session.flush()
        result = ConversationCreated(conversation_id=conversation.id)

    response.set_cookie(
        key=OWNER_COOKIE,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure or settings.environment == "production",
        samesite="lax",
        path=f"/api/v1/assistant/conversations/{result.conversation_id}",
    )
    response.headers.update(NO_STORE_HEADERS)
    return result


@router.get("/{conversation_id}", response_model=ConversationHistory)
def read_conversation(
    conversation_id: UUID,
    request: Request,
    response: Response,
    session: DatabaseSession,
) -> ConversationHistory:
    _require_owner(session, conversation_id, request.cookies.get(OWNER_COOKIE))

    rows = session.scalars(
        select(AssistantTurn)
        .where(AssistantTurn.conversation_id == conversation_id)
        .order_by(AssistantTurn.turn_number)
        .limit(MAX_TURNS)
    )

    result = ConversationHistory(
        conversation_id=conversation_id,
        turns=[
            ConversationTurn(
                turn_number=row.turn_number,
                question=row.question,
                answer=AssistantAnswer.model_validate(row.answer),
            )
            for row in rows
        ],
    )
    response.headers.update(NO_STORE_HEADERS)
    return result


@router.post("/{conversation_id}/turns", response_model=ConversationTurn, status_code=201)
def create_turn(
    conversation_id: UUID,
    data: AssistantQuestion,
    request: Request,
    response: Response,
    session: DatabaseSession,
    settings: IdentitySettings,
) -> ConversationTurn:
    validate_request_origin(request, settings)
    if "\x00" in data.question:
        raise HTTPException(status_code=422, headers=NO_STORE_HEADERS)

    with session.begin():
        _require_owner(session, conversation_id, request.cookies.get(OWNER_COOKIE), lock=True)
        last_turn = session.scalar(
            select(func.max(AssistantTurn.turn_number)).where(
                AssistantTurn.conversation_id == conversation_id
            )
        )
        turn_number = (last_turn or 0) + 1
        if turn_number > MAX_TURNS:
            raise HTTPException(status_code=409, headers=NO_STORE_HEADERS)

        answer = answer_policy_question(data)
        session.add(
            AssistantTurn(
                conversation_id=conversation_id,
                turn_number=turn_number,
                question=data.question,
                answer=answer.model_dump(mode="json"),
            )
        )
        result = ConversationTurn(
            turn_number=turn_number,
            question=data.question,
            answer=answer,
        )

    response.headers.update(NO_STORE_HEADERS)
    return result
