from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from railconnect.modules.incidents.report_schemas import (
    ReportSubmissionResponse,
    SubmitReportInput,
)


def report_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "title": "Passenger observation",
        "narrative": "A fictional service appears to be delayed.",
        "observed_at": "2026-10-14T14:00:00+05:30",
    }
    values.update(changes)
    return values


def test_accepts_report_without_scope_hints() -> None:
    report = SubmitReportInput.model_validate(report_values())

    assert report.title == "Passenger observation"
    assert report.observed_at.utcoffset() is not None
    assert report.run_hint_id is None
    assert report.station_hint_id is None


def test_strips_narrative_and_title_boundary_whitespace() -> None:
    report = SubmitReportInput.model_validate(
        report_values(
            title="  Passenger observation  ",
            narrative="  Fictional passenger claim.  ",
        )
    )

    assert report.title == "Passenger observation"
    assert report.narrative == "Fictional passenger claim."


def test_accepts_ordered_segment_hints() -> None:
    run_id = uuid4()

    report = SubmitReportInput.model_validate(
        report_values(
            run_hint_id=str(run_id),
            departure_stop_sequence_hint=1,
            arrival_stop_sequence_hint=3,
        )
    )

    assert report.run_hint_id == run_id
    assert report.departure_stop_sequence_hint == 1
    assert report.arrival_stop_sequence_hint == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "verified"),
        ("version", 10),
        ("submitted_by_user_id", str(uuid4())),
        ("reviewed_by_id", str(uuid4())),
        ("reviewed_at", "2026-10-14T09:00:00Z"),
        ("review_reason", "Passenger-assigned verification."),
        ("estimated_delay_minutes", 45),
        ("submitted_at", "2026-10-14T09:00:00Z"),
    ],
)
def test_rejects_server_owned_or_approved_fields(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SubmitReportInput.model_validate(report_values(**{field: value}))


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "   "},
        {"title": "x" * 161},
        {"narrative": "   "},
        {"narrative": "x" * 4001},
        {"observed_at": "2026-10-14T09:00:00"},
        {"run_hint_id": "invalid"},
        {"station_hint_id": "invalid"},
    ],
)
def test_rejects_invalid_report_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SubmitReportInput.model_validate(report_values(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": 1,
        },
        {
            "run_hint_id": str(uuid4()),
            "arrival_stop_sequence_hint": 3,
        },
        {
            "departure_stop_sequence_hint": 1,
            "arrival_stop_sequence_hint": 3,
        },
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": 3,
            "arrival_stop_sequence_hint": 1,
        },
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": 2,
            "arrival_stop_sequence_hint": 2,
        },
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": 0,
            "arrival_stop_sequence_hint": 3,
        },
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": "1",
            "arrival_stop_sequence_hint": 3,
        },
        {
            "run_hint_id": str(uuid4()),
            "departure_stop_sequence_hint": True,
            "arrival_stop_sequence_hint": 3,
        },
    ],
)
def test_rejects_invalid_segment_hints(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SubmitReportInput.model_validate(report_values(**changes))


def test_submission_response_contains_only_receipt_fields() -> None:
    response = ReportSubmissionResponse(
        report_id=uuid4(),
        status="pending",
        submitted_at=datetime(2026, 10, 14, 9, 0, tzinfo=UTC),
    )

    assert set(response.model_dump()) == {
        "report_id",
        "status",
        "submitted_at",
        "message",
    }
    assert response.status == "pending"


def test_submission_response_cannot_claim_verification() -> None:
    with pytest.raises(ValidationError):
        ReportSubmissionResponse.model_validate(
            {
                "report_id": str(uuid4()),
                "status": "verified",
                "submitted_at": "2026-10-14T09:00:00Z",
            }
        )
