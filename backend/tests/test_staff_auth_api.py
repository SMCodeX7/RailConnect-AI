from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.modules.identity.dependencies import (
    get_identity_clock,
    get_identity_session,
    require_staff_permission,
)
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import Permission, RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.identity.session_service import AuthenticatedSession

PASSWORD = "Fictional authentication API passphrase"
ORIGIN = "http://127.0.0.1:5173"
NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)


@dataclass
class AuthContext:
    client: TestClient
    database: Session
    user: User
    settings: Settings
    clock_value: list[datetime]


@pytest.fixture(scope="module")
def api_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def auth_context(
    identity_database: Session,
    api_password_hash: str,
) -> Iterator[AuthContext]:
    user = provision_staff_user(
        identity_database,
        ProvisionStaffInput(
            username=f"auth_{uuid4().hex}",
            display_name="Fictional API Staff",
            role=RoleCode.CONTROLLER,
        ),
        api_password_hash,
    )
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=None,
        session_cookie_secure=False,
        trusted_origins=[ORIGIN],
        login_account_max_attempts=3,
        login_client_max_attempts=30,
    )
    clock_value = [NOW]
    app = create_app(settings)

    def override_session() -> Iterator[Session]:
        with Session(
            bind=identity_database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_identity_session] = override_session
    app.dependency_overrides[get_identity_clock] = lambda: lambda: clock_value[0]

    @app.get("/api/v1/test/review")
    def review_permission(
        authenticated: Annotated[
            AuthenticatedSession,
            Depends(require_staff_permission(Permission.REPORTS_REVIEW)),
        ],
    ) -> dict[str, str]:
        return {"username": authenticated.actor.username}

    @app.get("/api/v1/test/timetable")
    def timetable_permission(
        authenticated: Annotated[
            AuthenticatedSession,
            Depends(require_staff_permission(Permission.TIMETABLE_MANAGE)),
        ],
    ) -> dict[str, str]:
        return {"username": authenticated.actor.username}

    try:
        with TestClient(app, base_url="https://testserver") as client:
            yield AuthContext(
                client=client,
                database=identity_database,
                user=user,
                settings=settings,
                clock_value=clock_value,
            )
    finally:
        app.dependency_overrides.clear()


def sign_in(context: AuthContext) -> str:
    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    assert isinstance(csrf_token, str)
    return csrf_token


def test_login_sets_cookie_and_returns_only_safe_fields(
    auth_context: AuthContext,
) -> None:
    context = auth_context
    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"actor", "csrf_token", "expires_at"}
    assert body["actor"]["username"] == context.user.username
    assert "password_hash" not in body["actor"]
    assert "token" not in body
    assert response.headers["Cache-Control"] == "no-store"

    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Domain=" not in cookie
    assert "Secure" not in cookie
    assert response.headers["X-Request-ID"]


def test_secure_configuration_sets_secure_cookie(
    auth_context: AuthContext,
) -> None:
    context = auth_context
    context.settings.session_cookie_secure = True

    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 200
    assert "Secure" in response.headers["Set-Cookie"]


def test_me_restores_authenticated_session(auth_context: AuthContext) -> None:
    csrf_token = sign_in(auth_context)

    response = auth_context.client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["actor"]["username"] == auth_context.user.username
    assert response.json()["csrf_token"] == csrf_token
    assert response.headers["Cache-Control"] == "no-store"


def test_me_without_cookie_returns_401(auth_context: AuthContext) -> None:
    response = auth_context.client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("unknown_user", [False, True])
def test_invalid_credentials_have_generic_response(
    auth_context: AuthContext,
    unknown_user: bool,
) -> None:
    username = f"unknown_{uuid4().hex}" if unknown_user else auth_context.user.username
    response = auth_context.client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "A wrong fictional passphrase"},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert response.headers["Cache-Control"] == "no-store"
    assert auth_context.settings.session_cookie_name not in auth_context.client.cookies


@pytest.mark.parametrize("origin", [None, "null", "https://untrusted.example"])
def test_login_rejects_missing_or_disallowed_origin(
    auth_context: AuthContext,
    origin: str | None,
) -> None:
    headers = {"Origin": origin} if origin is not None else {}
    response = auth_context.client.post(
        "/api/v1/auth/login",
        json={"username": auth_context.user.username, "password": PASSWORD},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_login_requires_json(auth_context: AuthContext) -> None:
    response = auth_context.client.post(
        "/api/v1/auth/login",
        content="username=staff&password=fictional",
        headers={
            "Origin": ORIGIN,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_logout_revokes_cookie_and_prevents_replay(
    auth_context: AuthContext,
) -> None:
    context = auth_context
    csrf_token = sign_in(context)
    token = context.client.cookies.get(context.settings.session_cookie_name)
    assert token is not None

    response = context.client.post(
        "/api/v1/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["Cache-Control"] == "no-store"
    assert context.settings.session_cookie_name not in context.client.cookies
    assert context.client.get("/api/v1/auth/me").status_code == 401

    context.client.cookies.set(context.settings.session_cookie_name, token)
    assert context.client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("csrf_token", [None, "invalid", "f" * 64])
def test_logout_rejects_missing_or_invalid_csrf(
    auth_context: AuthContext,
    csrf_token: str | None,
) -> None:
    sign_in(auth_context)
    headers = {"Origin": ORIGIN}
    if csrf_token is not None:
        headers["X-CSRF-Token"] = csrf_token

    response = auth_context.client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert auth_context.client.get("/api/v1/auth/me").status_code == 200


def test_logout_rejects_disallowed_origin(auth_context: AuthContext) -> None:
    csrf_token = sign_in(auth_context)

    response = auth_context.client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": "https://untrusted.example",
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 403
    assert auth_context.client.get("/api/v1/auth/me").status_code == 200


def test_disabled_user_loses_session_access(auth_context: AuthContext) -> None:
    sign_in(auth_context)
    auth_context.user.is_active = False
    auth_context.database.flush()

    response = auth_context.client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_role_removal_loses_session_access(auth_context: AuthContext) -> None:
    sign_in(auth_context)
    auth_context.database.execute(delete(UserRole).where(UserRole.user_id == auth_context.user.id))
    auth_context.database.flush()

    assert auth_context.client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("expiry", ["idle", "absolute"])
def test_expired_session_is_rejected(
    auth_context: AuthContext,
    expiry: str,
) -> None:
    context = auth_context
    sign_in(context)

    if expiry == "idle":
        context.clock_value[0] = NOW + timedelta(minutes=30)
    else:
        stored = context.database.scalar(
            select(AuthSession).where(AuthSession.user_id == context.user.id)
        )
        assert stored is not None
        stored.last_seen_at = stored.expires_at - timedelta(seconds=1)
        context.database.flush()
        context.clock_value[0] = stored.expires_at

    assert context.client.get("/api/v1/auth/me").status_code == 401


def test_permission_checks_allow_review_but_deny_timetable_management(
    auth_context: AuthContext,
) -> None:
    assert auth_context.client.get("/api/v1/test/review").status_code == 401
    sign_in(auth_context)

    assert auth_context.client.get("/api/v1/test/review").status_code == 200
    response = auth_context.client.get("/api/v1/test/timetable")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_failed_logins_lead_to_429_with_retry_after(
    auth_context: AuthContext,
) -> None:
    context = auth_context

    for _ in range(3):
        response = context.client.post(
            "/api/v1/auth/login",
            json={
                "username": context.user.username,
                "password": "A wrong fictional passphrase",
            },
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 401

    blocked = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
    assert blocked.headers["Retry-After"] == "300"
    assert blocked.headers["Cache-Control"] == "no-store"


def test_missing_database_returns_service_unavailable() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_url=None,
            session_cookie_secure=False,
            trusted_origins=[ORIGIN],
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "fictional_staff", "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
