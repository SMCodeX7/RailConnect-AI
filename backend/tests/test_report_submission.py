from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity.models.user import User
from railconnect.modules.incidents import report_service
from railconnect.modules.incidents.errors import (
    InvalidReportError,
    ReportRateLimitedError,
)
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit
from railconnect.modules.incidents.report_rate_service import report_limit_key
from railconnect.modules.incidents.report_schemas import SubmitReportInput
from railconnect.modules.incidents.report_service import submit_report

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def submission_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        report_rate_window_seconds=60,
        report_client_max_attempts=2,
    )


@pytest.fixture
def client_key() -> str:
    return f"submission-test-{uuid4().hex}"


@pytest.fixture
def report_input() -> SubmitReportInput:
    return SubmitReportInput(
        title=f"Submission test {uuid4().hex}",
        narrative="Synthetic passenger observation.",
        observed_at=NOW - timedelta(minutes=5),
    )


def submit_using_fresh_session(
    database: Session,
    data: SubmitReportInput,
    client: str,
    settings: Settings,
    actor_id: UUID | None = None,
):
    with Session(
        bind=database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        return submit_report(
            session,
            data,
            client,
            settings,
            clock=lambda: NOW,
            submitted_by_user_id=actor_id,
        )


def attempt_count(database: Session, client: str) -> int | None:
    return database.scalar(
        select(ReportRateLimit.attempt_count).where(
            ReportRateLimit.key_hash == report_limit_key(client)
        )
    )


def report_count(database: Session, title: str) -> int:
    count = database.scalar(
        select(func.count()).select_from(IncidentReport).where(IncidentReport.title == title)
    )
    assert count is not None
    return count


def test_creates_pending_report_and_receipt(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    response = submit_using_fresh_session(
        identity_database,
        report_input,
        client_key,
        submission_settings,
    )

    report = identity_database.get(IncidentReport, response.report_id)

    assert report is not None
    assert report.status == "pending"
    assert report.version == 1
    assert report.reviewed_by_id is None
    assert report.review_reason is None
    assert report.submitted_by_user_id is None
    assert report.submitted_at == NOW
    assert response.status == "pending"
    assert response.submitted_at == NOW
    assert attempt_count(identity_database, client_key) == 1


def test_records_server_supplied_staff_identity(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    user = User(
        username=f"submitter_{uuid4().hex}",
        display_name="Synthetic Staff Submitter",
        password_hash="unused-test-hash",
        is_active=True,
    )
    identity_database.add(user)
    identity_database.flush()

    response = submit_using_fresh_session(
        identity_database,
        report_input,
        client_key,
        submission_settings,
        actor_id=user.id,
    )

    report = identity_database.get(IncidentReport, response.report_id)
    assert report is not None
    assert report.submitted_by_user_id == user.id
    assert report.status == "pending"


def test_rejects_future_observation_but_preserves_counter(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    data = SubmitReportInput.model_validate(
        {
            **report_input.model_dump(),
            "observed_at": NOW + timedelta(seconds=1),
        }
    )

    with pytest.raises(InvalidReportError, match="cannot be in the future"):
        submit_using_fresh_session(
            identity_database,
            data,
            client_key,
            submission_settings,
        )

    assert attempt_count(identity_database, client_key) == 1
    assert report_count(identity_database, data.title) == 0


def test_accepts_observation_at_submission_time(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    data = SubmitReportInput.model_validate({**report_input.model_dump(), "observed_at": NOW})

    response = submit_using_fresh_session(
        identity_database,
        data,
        client_key,
        submission_settings,
    )

    assert response.status == "pending"


@pytest.mark.parametrize("field", ["run_hint_id", "station_hint_id"])
def test_rejects_missing_scope_reference(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
    field: str,
) -> None:
    data = SubmitReportInput.model_validate({**report_input.model_dump(), field: uuid4()})

    with pytest.raises(InvalidReportError):
        submit_using_fresh_session(
            identity_database,
            data,
            client_key,
            submission_settings,
        )

    assert attempt_count(identity_database, client_key) == 1
    assert report_count(identity_database, data.title) == 0


def test_rejects_unavailable_staff_submitter(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    with pytest.raises(InvalidReportError, match="staff account is unavailable"):
        submit_using_fresh_session(
            identity_database,
            report_input,
            client_key,
            submission_settings,
            actor_id=uuid4(),
        )

    assert attempt_count(identity_database, client_key) == 1
    assert report_count(identity_database, report_input.title) == 0


def test_rate_rejection_preserves_counter_without_creating_report(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    for _ in range(2):
        submit_using_fresh_session(
            identity_database,
            report_input,
            client_key,
            submission_settings,
        )

    with pytest.raises(ReportRateLimitedError) as captured:
        submit_using_fresh_session(
            identity_database,
            report_input,
            client_key,
            submission_settings,
        )

    assert captured.value.retry_after == 60
    assert attempt_count(identity_database, client_key) == 3
    assert report_count(identity_database, report_input.title) == 2


def test_report_failure_rolls_back_insert_but_preserves_counter(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_create = report_service.create_pending_report

    def fail_after_insert(
        session: Session,
        data: SubmitReportInput,
        submitted_at: datetime,
        submitted_by_user_id: UUID | None,
    ) -> IncidentReport:
        original_create(session, data, submitted_at, submitted_by_user_id)
        raise RuntimeError("Synthetic failure after report insert")

    monkeypatch.setattr(
        report_service,
        "create_pending_report",
        fail_after_insert,
    )

    with pytest.raises(RuntimeError, match="Synthetic failure"):
        submit_using_fresh_session(
            identity_database,
            report_input,
            client_key,
            submission_settings,
        )

    assert attempt_count(identity_database, client_key) == 1
    assert report_count(identity_database, report_input.title) == 0


def test_requires_fresh_session(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    with pytest.raises(ValueError, match="fresh session"):
        submit_report(
            identity_database,
            report_input,
            client_key,
            submission_settings,
            clock=lambda: NOW,
        )

    assert attempt_count(identity_database, client_key) is None


def test_rejects_naive_clock_before_writing_counter(
    identity_database: Session,
    submission_settings: Settings,
    client_key: str,
    report_input: SubmitReportInput,
) -> None:
    with Session(
        bind=identity_database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(ValueError, match="timezone-aware clock"):
            submit_report(
                session,
                report_input,
                client_key,
                submission_settings,
                clock=lambda: NOW.replace(tzinfo=None),
            )

    assert attempt_count(identity_database, client_key) is None
