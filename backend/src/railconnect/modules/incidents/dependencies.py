from collections.abc import Iterator
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    IdentityClock,
    IdentitySession,
    IdentitySettings,
    get_mutating_staff,
    validate_request_origin,
)


def get_report_session(request: Request) -> Iterator[Session]:
    factory = cast(
        sessionmaker[Session] | None,
        getattr(request.app.state, "session_factory", None),
    )

    if factory is None:
        raise HTTPException(status_code=503, headers=NO_STORE_HEADERS)

    try:
        with factory() as session:
            yield session
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            headers=NO_STORE_HEADERS,
        ) from error


ReportSession = Annotated[Session, Depends(get_report_session)]


def validate_report_request(
    request: Request,
    settings: IdentitySettings,
) -> None:
    validate_request_origin(request, settings)

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()

    if content_type != "application/json":
        raise HTTPException(status_code=415, headers=NO_STORE_HEADERS)


def get_optional_report_submitter(
    request: Request,
    session: IdentitySession,
    settings: IdentitySettings,
    clock: IdentityClock,
) -> UUID | None:
    if settings.session_cookie_name not in request.cookies:
        return None

    authenticated = get_mutating_staff(
        request=request,
        session=session,
        settings=settings,
        clock=clock,
    )

    return UUID(authenticated.actor.user_id)


ReportSubmitter = Annotated[
    UUID | None,
    Depends(get_optional_report_submitter),
]
