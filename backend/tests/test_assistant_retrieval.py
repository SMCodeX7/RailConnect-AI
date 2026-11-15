import pytest

from railconnect.modules.assistant.passenger_guide_v1 import PASSENGER_GUIDE_V1
from railconnect.modules.assistant.retrieval import PolicyChunk, search_policy

REPORTING = PolicyChunk(
    source_id="passenger-guide",
    source_version="1",
    chunk_id="report-a-disruption",
    title="Report a disruption",
    text="Submit a passenger report when you observe a service disruption.",
)
SCHEDULE = PolicyChunk(
    source_id="passenger-guide",
    source_version="1",
    chunk_id="demo-schedule",
    title="Demonstration schedule",
    text="Search the prepared timetable for scheduled services.",
)


def test_policy_search_returns_a_citable_chunk() -> None:
    matches = search_policy("How do I REPORT a disruption?", [SCHEDULE, REPORTING])

    assert matches == [REPORTING]
    assert matches[0].chunk_id == "report-a-disruption"


def test_policy_search_returns_no_unrelated_evidence() -> None:
    assert search_policy("Where can I buy a ticket?", [REPORTING, SCHEDULE]) == []


def test_policy_search_breaks_ties_by_stable_reference() -> None:
    first = PolicyChunk("guide", "1", "a", "Journey search", "Search by station.")
    second = PolicyChunk("guide", "1", "b", "Journey search", "Search by date.")

    assert search_policy("Journey search", [second, first], limit=1) == [first]


def test_policy_search_rejects_an_unbounded_result_limit() -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        search_policy("disruption", [REPORTING], limit=6)


@pytest.mark.parametrize(
    ("question", "expected_chunk_id"),
    [
        ("How do I report a disruption?", "report-disruption"),
        ("How do I check direct alternatives?", "check-direct-alternatives"),
        ("Is the timetable fictional demonstration data?", "demonstration-coverage"),
    ],
)
def test_passenger_guide_returns_expected_source(
    question: str,
    expected_chunk_id: str,
) -> None:
    matches = search_policy(question, PASSENGER_GUIDE_V1, limit=1)

    assert len(matches) == 1
    assert matches[0].source_id == "railconnect-passenger-guide"
    assert matches[0].source_version == "1"
    assert matches[0].chunk_id == expected_chunk_id


def test_passenger_guide_has_unique_citation_references() -> None:
    references = {
        (chunk.source_id, chunk.source_version, chunk.chunk_id) for chunk in PASSENGER_GUIDE_V1
    }

    assert len(references) == len(PASSENGER_GUIDE_V1)
