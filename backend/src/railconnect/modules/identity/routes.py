from fastapi import APIRouter, Depends, HTTPException, Request, Response

from railconnect.modules.identity.auth_schemas import LoginInput, StaffSessionResponse
from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    CurrentStaff,
    IdentityClock,
    IdentitySession,
    IdentitySettings,
    MutatingStaff,
    get_staff_cookie,
    validate_login_request,
)
from railconnect.modules.identity.errors import AuthenticationError, LoginRateLimitError
from railconnect.modules.identity.login_service import login_staff
from railconnect.modules.identity.session_service import revoke_staff_session

router = APIRouter(prefix="/auth", tags=["Staff authentication"])


@router.post(
    "/login",
    response_model=StaffSessionResponse,
    dependencies=[Depends(validate_login_request)],
)
def login(
    data: LoginInput,
    request: Request,
    response: Response,
    session: IdentitySession,
    settings: IdentitySettings,
    clock: IdentityClock,
) -> StaffSessionResponse:
    if request.client is None:
        raise HTTPException(status_code=503, headers=NO_STORE_HEADERS)

    try:
        created = login_staff(
            session,
            data,
            request.client.host,
            settings,
            clock,
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            headers=NO_STORE_HEADERS,
        ) from error
    except LoginRateLimitError as error:
        raise HTTPException(
            status_code=429,
            headers={
                **NO_STORE_HEADERS,
                "Retry-After": str(error.retry_after),
            },
        ) from error

    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=settings.session_cookie_name,
        value=created.token,
        max_age=settings.session_ttl_seconds,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    return StaffSessionResponse(
        actor=created.actor,
        csrf_token=created.csrf_token,
        expires_at=created.expires_at,
    )


@router.get("/me", response_model=StaffSessionResponse)
def current_session(
    response: Response,
    authenticated: CurrentStaff,
) -> StaffSessionResponse:
    response.headers["Cache-Control"] = "no-store"

    return StaffSessionResponse(
        actor=authenticated.actor,
        csrf_token=authenticated.csrf_token,
        expires_at=authenticated.expires_at,
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    authenticated: MutatingStaff,
    session: IdentitySession,
    settings: IdentitySettings,
    clock: IdentityClock,
) -> Response:
    token = get_staff_cookie(request, settings)

    try:
        with session.begin():
            revoke_staff_session(session, token, settings, clock())
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            headers=NO_STORE_HEADERS,
        ) from error

    response = Response(status_code=204, headers=NO_STORE_HEADERS)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response
