from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, or_, select, tuple_
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit


def _session_candidates(
    cutoff: datetime,
    batch_size: int,
) -> Select[UUID]:
    return (
        select(AuthSession.id)
        .where(
            or_(
                AuthSession.expires_at <= cutoff,
                AuthSession.revoked_at <= cutoff,
            )
        )
        .order_by(AuthSession.expires_at, AuthSession.id)
        .limit(batch_size)
    )


def _rate_candidates(
    cutoff: datetime,
    batch_size: int,
) -> Select[str, str]:
    return (
        select(LoginRateLimit.scope, LoginRateLimit.key_hash)
        .where(LoginRateLimit.window_expires_at <= cutoff)
        .order_by(
            LoginRateLimit.window_expires_at,
            LoginRateLimit.scope,
            LoginRateLimit.key_hash,
        )
        .limit(batch_size)
    )


def preview_cleanup(
    session: Session,
    session_cutoff: datetime,
    rate_cutoff: datetime,
    batch_size: int,
) -> tuple[int, int]:
    sessions = list(session.scalars(_session_candidates(session_cutoff, batch_size)))
    rate_rows = session.execute(_rate_candidates(rate_cutoff, batch_size)).all()
    return len(sessions), len(rate_rows)


def apply_cleanup(
    session: Session,
    session_cutoff: datetime,
    rate_cutoff: datetime,
    batch_size: int,
) -> tuple[int, int]:
    session_candidates = _session_candidates(session_cutoff, batch_size).with_for_update(
        skip_locked=True
    )

    deleted_sessions = list(
        session.scalars(
            delete(AuthSession)
            .where(AuthSession.id.in_(session_candidates))
            .returning(AuthSession.id)
        )
    )

    rate_candidates = _rate_candidates(rate_cutoff, batch_size).with_for_update(skip_locked=True)

    deleted_rates = session.execute(
        delete(LoginRateLimit)
        .where(tuple_(LoginRateLimit.scope, LoginRateLimit.key_hash).in_(rate_candidates))
        .returning(LoginRateLimit.scope, LoginRateLimit.key_hash)
    ).all()

    return len(deleted_sessions), len(deleted_rates)
