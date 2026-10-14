from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from railconnect.core.clock import utc_now
from railconnect.core.config import Settings
from railconnect.modules.identity.errors import (
    AuthenticationError,
    PermissionDeniedError,
)
from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    authenticate_staff_session,
    require_actor_permission,
    verify_session_csrf,
)

NO_STORE_HEADERS = {"Cache-Control": "no-store"}


def get_identity_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_identity_clock() -> Callable[[], datetime]:
    return utc_now


def get_identity_session(request: Request) -> Iterator[Session]:
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


IdentitySession = Annotated[Session, Depends(get_identity_session)]
IdentitySettings = Annotated[Settings, Depends(get_identity_settings)]
IdentityClock = Annotated[Callable[[], datetime], Depends(get_identity_clock)]


def validate_request_origin(request: Request, settings: Settings) -> None:
    origins = request.headers.getlist("origin")

    if len(origins) != 1 or origins[0] not in settings.trusted_origins:
        raise HTTPException(status_code=403, headers=NO_STORE_HEADERS)

    if settings.environment == "production" and request.url.scheme != "https":
        raise HTTPException(status_code=403, headers=NO_STORE_HEADERS)


def validate_login_request(
    request: Request,
    settings: IdentitySettings,
) -> None:
    validate_request_origin(request, settings)

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, headers=NO_STORE_HEADERS)


def get_staff_cookie(request: Request, settings: Settings) -> str:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, headers=NO_STORE_HEADERS)
    return token


def get_current_staff(
    request: Request,
    session: IdentitySession,
    settings: IdentitySettings,
    clock: IdentityClock,
) -> AuthenticatedSession:
    token = get_staff_cookie(request, settings)

    try:
        with session.begin():
            return authenticate_staff_session(session, token, settings, clock())
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            headers=NO_STORE_HEADERS,
        ) from error


def get_mutating_staff(
    request: Request,
    session: IdentitySession,
    settings: IdentitySettings,
    clock: IdentityClock,
) -> AuthenticatedSession:
    validate_request_origin(request, settings)
    token = get_staff_cookie(request, settings)
    csrf_tokens = request.headers.getlist("x-csrf-token")

    if len(csrf_tokens) != 1:
        raise HTTPException(status_code=403, headers=NO_STORE_HEADERS)

    try:
        with session.begin():
            authenticated = authenticate_staff_session(session, token, settings, clock())
            verify_session_csrf(authenticated, csrf_tokens[0])
            return authenticated
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            headers=NO_STORE_HEADERS,
        ) from error
    except PermissionDeniedError as error:
        raise HTTPException(
            status_code=403,
            headers=NO_STORE_HEADERS,
        ) from error


CurrentStaff = Annotated[AuthenticatedSession, Depends(get_current_staff)]
MutatingStaff = Annotated[AuthenticatedSession, Depends(get_mutating_staff)]


def require_staff_permission(
    permission: Permission,
    mutation: bool = False,
) -> Callable[..., AuthenticatedSession]:
    authentication = get_mutating_staff if mutation else get_current_staff

    def dependency(
        authenticated: Annotated[
            AuthenticatedSession,
            Depends(authentication),
        ],
    ) -> AuthenticatedSession:
        try:
            require_actor_permission(authenticated.actor, permission)
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=403,
                headers=NO_STORE_HEADERS,
            ) from error
        return authenticated

    return dependency
