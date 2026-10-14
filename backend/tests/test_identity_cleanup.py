from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.identity.cleanup_service import cleanup_identity_records
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.identity.tokens import (
    generate_csrf_token,
    generate_session_token,
    hash_session_token,
)

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


@pytest.fixture(scope="module")
def cleanup_password_hash() -> str:
    return hash_password("Fictional cleanup test passphrase")


@pytest.fixture
def cleanup_user(
    identity_database: Session,
    cleanup_password_hash: str,
) -> User:
    return provision_staff_user(
        identity_database,
        ProvisionStaffInput(
            username=f"cleanup_{uuid4().hex}",
            display_name="Cleanup Test Staff",
            role=RoleCode.CONTROLLER,
        ),
        cleanup_password_hash,
    )


def add_session(
    session: Session,
    user: User,
    *,
    created_at: datetime,
    expires_at: datetime,
    revoked_at: datetime | None = None,
) -> UUID:
    record = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(generate_session_token()),
        csrf_token=generate_csrf_token(),
        auth_version=user.auth_version,
        created_at=created_at,
        last_seen_at=created_at,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )
    session.add(record)
    session.flush()
    return record.id


def add_rate_limit(session: Session, expires_at: datetime) -> str:
    key = uuid4().hex + uuid4().hex
    session.add(
        LoginRateLimit(
            scope="client",
            key_hash=key,
            attempt_count=1,
            window_started_at=expires_at - timedelta(minutes=5),
            window_expires_at=expires_at,
        )
    )
    session.flush()
    return key


def counts(session: Session) -> tuple[int, int]:
    sessions = session.scalar(select(func.count()).select_from(AuthSession))
    rates = session.scalar(select(func.count()).select_from(LoginRateLimit))
    assert sessions is not None
    assert rates is not None
    return sessions, rates


def test_preview_preserves_records(
    identity_database: Session,
    cleanup_user: User,
) -> None:
    session = identity_database
    session_id = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(days=10),
        expires_at=NOW - timedelta(days=9),
    )
    rate_key = add_rate_limit(session, NOW - timedelta(days=2))
    before = counts(session)

    result = cleanup_identity_records(session, NOW)

    assert result.applied is False
    assert result.sessions >= 1
    assert result.login_limits >= 1
    assert counts(session) == before
    assert session.get(AuthSession, session_id) is not None
    assert session.get(LoginRateLimit, ("client", rate_key)) is not None


def test_apply_removes_old_records_and_preserves_recent_records(
    identity_database: Session,
    cleanup_user: User,
) -> None:
    session = identity_database
    old_session = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(days=10),
        expires_at=NOW - timedelta(days=9),
    )
    old_revoked = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(days=7, hours=1),
        expires_at=NOW - timedelta(days=6, hours=23),
        revoked_at=NOW - timedelta(days=7),
    )
    recent_expired = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(days=2),
        expires_at=NOW - timedelta(days=1),
    )
    active_session = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=7),
    )
    old_rate = add_rate_limit(session, NOW - timedelta(days=2))
    recent_rate = add_rate_limit(session, NOW - timedelta(hours=1))
    active_rate = add_rate_limit(session, NOW + timedelta(minutes=5))

    result = cleanup_identity_records(session, NOW, apply=True)

    assert result.applied is True
    assert session.get(AuthSession, old_session) is None
    assert session.get(AuthSession, old_revoked) is None
    assert session.get(AuthSession, recent_expired) is not None
    assert session.get(AuthSession, active_session) is not None
    assert session.get(LoginRateLimit, ("client", old_rate)) is None
    assert session.get(LoginRateLimit, ("client", recent_rate)) is not None
    assert session.get(LoginRateLimit, ("client", active_rate)) is not None
    assert session.get(User, cleanup_user.id) is not None
    assert session.scalar(select(UserRole).where(UserRole.user_id == cleanup_user.id)) is not None


def test_batch_size_bounds_deletion_per_table(
    identity_database: Session,
    cleanup_user: User,
) -> None:
    session = identity_database

    for _ in range(5):
        add_session(
            session,
            cleanup_user,
            created_at=NOW - timedelta(days=30),
            expires_at=NOW - timedelta(days=29),
        )
        add_rate_limit(session, NOW - timedelta(days=20))

    before_sessions, before_rates = counts(session)
    result = cleanup_identity_records(session, NOW, apply=True, batch_size=2)
    after_sessions, after_rates = counts(session)

    assert result.sessions == 2
    assert result.login_limits == 2
    assert before_sessions - after_sessions == 2
    assert before_rates - after_rates == 2


def test_caller_rollback_restores_deleted_records(
    identity_database: Session,
    cleanup_user: User,
) -> None:
    session = identity_database
    session_id = add_session(
        session,
        cleanup_user,
        created_at=NOW - timedelta(days=10),
        expires_at=NOW - timedelta(days=9),
    )
    rate_key = add_rate_limit(session, NOW - timedelta(days=2))
    before = counts(session)

    with pytest.raises(RuntimeError, match="abort cleanup"):
        with session.begin_nested():
            cleanup_identity_records(session, NOW, apply=True)
            raise RuntimeError("abort cleanup")

    assert counts(session) == before
    assert session.get(AuthSession, session_id) is not None
    assert session.get(LoginRateLimit, ("client", rate_key)) is not None


@pytest.mark.parametrize("at_boundary", [False, True])
def test_session_retention_boundary(
    identity_database: Session,
    cleanup_user: User,
    at_boundary: bool,
) -> None:
    session = identity_database
    expiry = NOW - timedelta(days=7)
    if not at_boundary:
        expiry += timedelta(seconds=1)

    session_id = add_session(
        session,
        cleanup_user,
        created_at=expiry - timedelta(hours=8),
        expires_at=expiry,
    )

    cleanup_identity_records(session, NOW, apply=True)

    assert (session.get(AuthSession, session_id) is None) is at_boundary


@pytest.mark.parametrize("at_boundary", [False, True])
def test_rate_retention_boundary(
    identity_database: Session,
    at_boundary: bool,
) -> None:
    expiry = NOW - timedelta(days=1)
    if not at_boundary:
        expiry += timedelta(seconds=1)

    key = add_rate_limit(identity_database, expiry)

    cleanup_identity_records(identity_database, NOW, apply=True)

    assert (identity_database.get(LoginRateLimit, ("client", key)) is None) is at_boundary


@pytest.mark.parametrize(
    "options",
    [
        {"batch_size": 0},
        {"batch_size": 1001},
        {"session_retention_days": 0},
        {"rate_retention_days": 0},
    ],
)
def test_invalid_cleanup_options_are_rejected(
    identity_database: Session,
    options: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        cleanup_identity_records(identity_database, NOW, **options)


def test_naive_clock_is_rejected(identity_database: Session) -> None:
    with pytest.raises(ValueError, match="timezone-aware clock"):
        cleanup_identity_records(
            identity_database,
            datetime(2026, 10, 14, 12),
        )


def test_requires_caller_owned_transaction(identity_database: Session) -> None:
    with Session(bind=identity_database.get_bind()) as separate_session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            cleanup_identity_records(separate_session, NOW)
