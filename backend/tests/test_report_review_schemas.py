from uuid import uuid4

import pytest
from pydantic import ValidationError

from railconnect.modules.incidents.review_schemas import (
    ApprovedIncidentInput,
    RejectReportInput,
    ReportReviewResponse,
    VerifyReportInput,
)


def approved_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": str(uuid4()),
        "scope_kind": "segment",
        "departure_stop_sequence": 1,
        "arrival_stop_sequence": 3,
        "impact_kind": "delay",
        "estimated_delay_minutes": 15,
        "effective_from": "2026-10-18T10:00:00+05:30",
        "effective_until": "2026-10-18T12:00:00+05:30",
        "public_summary": "Synthetic demonstration delay.",
        "evidence_basis": "Controller-reviewed synthetic scenario.",
    }
    values.update(changes)
    return values


def test_accepts_explicit_approved_delay() -> None:
    data = VerifyReportInput.model_validate(
        {
            "expected_version": 1,
            "reason": "Reviewed synthetic evidence.",
            "approved": approved_values(),
        }
    )

    assert data.expected_version == 1
    assert data.approved.estimated_delay_minutes == 15


def test_accepts_whole_run_cancellation() -> None:
    data = ApprovedIncidentInput.model_validate(
        approved_values(
            scope_kind="run",
            departure_stop_sequence=None,
            arrival_stop_sequence=None,
            impact_kind="cancellation",
            estimated_delay_minutes=None,
        )
    )

    assert data.scope_kind == "run"
    assert data.impact_kind == "cancellation"


def test_accepts_segment_restriction() -> None:
    data = ApprovedIncidentInput.model_validate(
        approved_values(
            impact_kind="restriction",
            estimated_delay_minutes=None,
        )
    )

    assert data.impact_kind == "restriction"


@pytest.mark.parametrize(
    "changes",
    [
        {"run_id": "invalid"},
        {"scope_kind": "station"},
        {"departure_stop_sequence": None},
        {"arrival_stop_sequence": None},
        {"departure_stop_sequence": 0},
        {"departure_stop_sequence": "1"},
        {"arrival_stop_sequence": 1},
        {"arrival_stop_sequence": True},
        {"scope_kind": "run"},
        {"impact_kind": "cancellation", "estimated_delay_minutes": None},
        {"impact_kind": "delay", "estimated_delay_minutes": None},
        {"estimated_delay_minutes": 0},
        {"estimated_delay_minutes": 1441},
        {"estimated_delay_minutes": "15"},
        {"estimated_delay_minutes": True},
        {"impact_kind": "restriction"},
        {"effective_from": "2026-10-18T10:00:00"},
        {"effective_until": "2026-10-18T12:00:00"},
        {"effective_until": "2026-10-18T10:00:00+05:30"},
        {"effective_until": "2026-10-18T09:00:00+05:30"},
        {"public_summary": "   "},
        {"public_summary": "x" * 1001},
        {"evidence_basis": "   "},
        {"evidence_basis": "x" * 2001},
    ],
)
def test_rejects_invalid_approved_facts(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ApprovedIncidentInput.model_validate(approved_values(**changes))


@pytest.mark.parametrize("version", [0, -1, "1", True])
def test_rejects_invalid_expected_version(version: object) -> None:
    with pytest.raises(ValidationError):
        RejectReportInput.model_validate(
            {
                "expected_version": version,
                "reason": "Synthetic review reason.",
            }
        )


@pytest.mark.parametrize("reason", ["   ", "x" * 2001])
def test_rejects_invalid_review_reason(reason: str) -> None:
    with pytest.raises(ValidationError):
        RejectReportInput.model_validate({"expected_version": 1, "reason": reason})


def test_verification_requires_approved_facts() -> None:
    with pytest.raises(ValidationError):
        VerifyReportInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Missing approved operational facts.",
            }
        )


@pytest.mark.parametrize(
    "field",
    ["reviewed_by_id", "reviewed_at", "request_id", "status"],
)
def test_rejects_client_supplied_review_metadata(field: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        VerifyReportInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Synthetic review reason.",
                "approved": approved_values(),
                field: "client-supplied",
            }
        )


def test_rejection_cannot_include_approved_incident() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RejectReportInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Insufficient evidence.",
                "approved": approved_values(),
            }
        )


def test_accepts_verified_response_with_references() -> None:
    response = ReportReviewResponse(
        report_id=uuid4(),
        status="verified",
        report_version=2,
        incident_id=uuid4(),
        revision_id=uuid4(),
        incident_version=1,
    )

    assert response.status == "verified"


def test_verified_response_requires_references() -> None:
    with pytest.raises(ValidationError):
        ReportReviewResponse(
            report_id=uuid4(),
            status="verified",
            report_version=2,
        )


def test_accepts_rejected_response_without_incident() -> None:
    response = ReportReviewResponse(
        report_id=uuid4(),
        status="rejected",
        report_version=2,
    )

    assert response.incident_id is None
    assert response.revision_id is None
    assert response.incident_version is None


def test_rejected_response_cannot_reference_incident() -> None:
    with pytest.raises(ValidationError):
        ReportReviewResponse(
            report_id=uuid4(),
            status="rejected",
            report_version=2,
            incident_id=uuid4(),
        )
