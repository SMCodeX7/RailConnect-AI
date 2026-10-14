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
    session_ids = session.scalars(_session_candidates(session_cutoff, batch_size)).all()
    rate_rows = session.execute(_rate_candidates(rate_cutoff, batch_size)).all()

    return len(session_ids), len(rate_rows)


def apply_cleanup(
    session: Session,
    session_cutoff: datetime,
    rate_cutoff: datetime,
    batch_size: int,
) -> tuple[int, int]:
    session_ids = session.scalars(
        _session_candidates(session_cutoff, batch_size).with_for_update(skip_locked=True)
    ).all()

    deleted_sessions = 0

    if session_ids:
        deleted_sessions = len(
            session.scalars(
                delete(AuthSession)
                .where(AuthSession.id.in_(session_ids))
                .returning(AuthSession.id)
                .execution_options(synchronize_session="fetch")
            ).all()
        )

    rate_rows = session.execute(
        _rate_candidates(rate_cutoff, batch_size).with_for_update(skip_locked=True)
    ).all()
    rate_keys = [(scope, key_hash) for scope, key_hash in rate_rows]

    deleted_rates = 0

    if rate_keys:
        deleted_rates = len(
            session.execute(
                delete(LoginRateLimit)
                .where(
                    tuple_(
                        LoginRateLimit.scope,
                        LoginRateLimit.key_hash,
                    ).in_(rate_keys)
                )
                .returning(LoginRateLimit.scope, LoginRateLimit.key_hash)
                .execution_options(synchronize_session="fetch")
            ).all()
        )

    return deleted_sessions, deleted_rates
