from uuid import uuid4

import pytest
from pydantic import ValidationError

from railconnect.modules.incidents.lifecycle_schemas import (
    AmendIncidentInput,
    IncidentLifecycleResponse,
    ResolveIncidentInput,
)


def approved_values() -> dict[str, object]:
    return {
        "run_id": str(uuid4()),
        "scope_kind": "run",
        "impact_kind": "delay",
        "estimated_delay_minutes": 20,
        "effective_from": "2026-10-18T10:00:00+05:30",
        "effective_until": "2026-10-18T14:00:00+05:30",
        "public_summary": "Updated synthetic delay.",
        "evidence_basis": "Reviewed synthetic evidence.",
    }


def test_accepts_amendment_with_explicit_approved_facts() -> None:
    data = AmendIncidentInput.model_validate(
        {
            "expected_version": 1,
            "reason": "Corrected synthetic estimate.",
            "approved": approved_values(),
        }
    )

    assert data.expected_version == 1
    assert data.approved.estimated_delay_minutes == 20


def test_amendment_requires_approved_facts() -> None:
    with pytest.raises(ValidationError):
        AmendIncidentInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Missing approved facts.",
            }
        )


def test_accepts_timezone_aware_resolution() -> None:
    data = ResolveIncidentInput.model_validate(
        {
            "expected_version": 2,
            "reason": "Synthetic disruption ended.",
            "resolution_effective_at": "2026-10-18T12:00:00+05:30",
        }
    )

    assert data.resolution_effective_at.utcoffset() is not None


@pytest.mark.parametrize("version", [0, -1, "1", True])
def test_rejects_invalid_expected_version(version: object) -> None:
    with pytest.raises(ValidationError):
        ResolveIncidentInput.model_validate(
            {
                "expected_version": version,
                "reason": "Synthetic resolution.",
                "resolution_effective_at": "2026-10-18T12:00:00Z",
            }
        )


@pytest.mark.parametrize("reason", ["   ", "x" * 2001])
def test_rejects_invalid_resolution_reason(reason: str) -> None:
    with pytest.raises(ValidationError):
        ResolveIncidentInput.model_validate(
            {
                "expected_version": 1,
                "reason": reason,
                "resolution_effective_at": "2026-10-18T12:00:00Z",
            }
        )


def test_resolution_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        ResolveIncidentInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Synthetic resolution.",
                "resolution_effective_at": "2026-10-18T12:00:00",
            }
        )


@pytest.mark.parametrize(
    "field",
    ["resolved_by_id", "resolved_at", "status", "request_id"],
)
def test_resolution_rejects_server_owned_fields(field: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ResolveIncidentInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Synthetic resolution.",
                "resolution_effective_at": "2026-10-18T12:00:00Z",
                field: "client-supplied",
            }
        )


def test_amendment_reuses_approved_impact_validation() -> None:
    approved = approved_values()
    approved["estimated_delay_minutes"] = 0

    with pytest.raises(ValidationError):
        AmendIncidentInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Invalid synthetic amendment.",
                "approved": approved,
            }
        )


def test_response_identifies_current_revision() -> None:
    revision_id = uuid4()
    response = IncidentLifecycleResponse(
        incident_id=uuid4(),
        originating_report_id=uuid4(),
        status="active",
        incident_version=2,
        current_revision_number=2,
        current_revision_id=revision_id,
    )

    assert response.current_revision_id == revision_id
    assert response.incident_version == 2
