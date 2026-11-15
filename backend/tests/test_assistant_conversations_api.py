from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session
from railconnect.modules.assistant.routes import OWNER_COOKIE

BASE_URL = "/api/v1/assistant/conversations"
ORIGIN = {"Origin": "http://127.0.0.1:5173"}


@pytest.fixture
def assistant_client(identity_database: Session) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_url=None,
            session_cookie_secure=False,
            trusted_origins=[ORIGIN["Origin"]],
        )
    )

    def override_session() -> Iterator[Session]:
        with Session(
            bind=identity_database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app, base_url="http://testserver") as client:
        yield client


def _create_conversation(client: TestClient) -> str:
    response = client.post(BASE_URL, headers=ORIGIN)
    assert response.status_code == 201, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert "httponly" in response.headers["Set-Cookie"].lower()
    assert set(response.json()) == {"conversation_id"}
    return f"{BASE_URL}/{response.json()['conversation_id']}"


def test_owner_can_append_and_read_cited_turns(assistant_client: TestClient) -> None:
    url = _create_conversation(assistant_client)
    empty = assistant_client.get(url)
    assert empty.status_code == 200, empty.text
    assert empty.json()["turns"] == []

    first = assistant_client.post(
        f"{url}/turns",
        headers=ORIGIN,
        json={"question": "How do I report a disruption?"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["turn_number"] == 1
    assert first.json()["answer"]["citations"][0]["chunk_id"] == "report-disruption"

    second = assistant_client.post(
        f"{url}/turns",
        headers=ORIGIN,
        json={"question": "What is the ticket price?"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["turn_number"] == 2
    assert second.json()["answer"]["status"] == "unavailable"

    history = assistant_client.get(url)
    assert history.status_code == 200, history.text
    assert history.headers["Cache-Control"] == "no-store"
    assert history.json()["turns"] == [first.json(), second.json()]


def test_missing_or_wrong_guest_cookie_blocks_access(assistant_client: TestClient) -> None:
    original_url = _create_conversation(assistant_client)
    assistant_client.cookies.clear()

    assert assistant_client.get(original_url).status_code == 404

    other_url = _create_conversation(assistant_client)
    other_cookie = assistant_client.cookies.get(OWNER_COOKIE, path=other_url)
    assert other_cookie is not None
    assistant_client.cookies.set(OWNER_COOKIE, other_cookie, path=original_url)

    assert assistant_client.get(original_url).status_code == 404
    rejected = assistant_client.post(
        f"{original_url}/turns",
        headers=ORIGIN,
        json={"question": "How do I report a disruption?"},
    )
    assert rejected.status_code == 404

    own_history = assistant_client.get(other_url)
    assert own_history.status_code == 200
    assert own_history.json()["turns"] == []


def test_untrusted_origin_cannot_create_or_append(assistant_client: TestClient) -> None:
    untrusted = {"Origin": "https://untrusted.example"}
    assert assistant_client.post(BASE_URL, headers=untrusted).status_code == 403

    url = _create_conversation(assistant_client)
    blocked = assistant_client.post(
        f"{url}/turns",
        headers=untrusted,
        json={"question": "How do I report a disruption?"},
    )
    assert blocked.status_code == 403

    history = assistant_client.get(url)
    assert history.status_code == 200
    assert history.json()["turns"] == []


@pytest.mark.parametrize(
    ("lookup", "expected_status", "expected_text"),
    [
        (
            {"kind": "journey", "departure": "Jaffna"},
            "clarify",
            "Enter the departure station, arrival station and boarding date.",
        ),
        (
            {"kind": "incident"},
            "clarify",
            "Enter the public incident ID you want to look up.",
        ),
        (
            {"kind": "incident", "incident_id": "00000000-0000-0000-0000-000000000001"},
            "unavailable",
            "No public verified incident matches that ID.",
        ),
    ],
)
def test_lookup_turn_requests_details_or_returns_unavailable(
    assistant_client: TestClient,
    lookup: dict[str, str],
    expected_status: str,
    expected_text: str,
) -> None:
    url = _create_conversation(assistant_client)
    response = assistant_client.post(
        f"{url}/turns",
        headers=ORIGIN,
        json={"question": "Help me check this record.", "lookup": lookup},
    )

    assert response.status_code == 201, response.text
    assert response.json()["answer"] == {
        "status": expected_status,
        "answer": expected_text,
        "citations": [],
    }


@pytest.mark.parametrize(
    "turns",
    [
        pytest.param(
            [
                ({"question": "How do I report a disruption?"}, "report-disruption"),
                ({"question": "Why is my submitted report pending?"}, "report-disruption"),
            ],
            id="report-then-pending-status",
        ),
        pytest.param(
            [
                ({"question": "How do I search for a direct journey?"}, "search-direct-journeys"),
                (
                    {"question": "How do I search for an overnight journey?"},
                    "search-direct-journeys",
                ),
            ],
            id="journey-search-then-overnight",
        ),
        pytest.param(
            [
                ({"question": "How do I refresh journey details?"}, "interpret-delay-estimates"),
                ({"question": "What does estimated arrival mean?"}, "interpret-delay-estimates"),
            ],
            id="refresh-then-estimated-arrival",
        ),
        pytest.param(
            [
                ({"question": "How do I find direct alternatives?"}, "check-direct-alternatives"),
                (
                    {"question": "Does the demo timetable cover every route?"},
                    "demonstration-coverage",
                ),
            ],
            id="alternatives-then-coverage",
        ),
        pytest.param(
            [
                ({"question": "What is the ticket price?"}, "unavailable"),
                ({"question": "Can I find a journey by station?"}, "search-direct-journeys"),
            ],
            id="fare-fallback-then-supported-search",
        ),
        pytest.param(
            [
                ({"question": "Is the demo timetable fictional?"}, "demonstration-coverage"),
                ({"question": "Where is my train on the live GPS map?"}, "unavailable"),
            ],
            id="demo-coverage-then-live-location",
        ),
        pytest.param(
            [
                ({"question": "How do I submit a disruption report?"}, "report-disruption"),
                (
                    {"question": "Who verified the delay and where are their private notes?"},
                    "unavailable",
                ),
            ],
            id="public-guidance-then-private-notes",
        ),
        pytest.param(
            [
                ({"question": "Which platform does the train use?"}, "unavailable"),
                ({"question": "Is bicycle carriage allowed?"}, "unavailable"),
            ],
            id="two-unsupported-requests",
        ),
        pytest.param(
            [
                ({"question": "Find a journey.", "lookup": {"kind": "journey"}}, "clarify"),
                (
                    {
                        "question": "Depart from Jaffna.",
                        "lookup": {"kind": "journey", "departure": "Jaffna"},
                    },
                    "clarify",
                ),
            ],
            id="journey-incomplete-after-follow-up",
        ),
        pytest.param(
            [
                (
                    {"question": "Look up an incident.", "lookup": {"kind": "incident"}},
                    "clarify",
                ),
                (
                    {
                        "question": "Try this public incident ID.",
                        "lookup": {
                            "kind": "incident",
                            "incident_id": "00000000-0000-0000-0000-000000000001",
                        },
                    },
                    "unavailable",
                ),
            ],
            id="incident-clarification-then-missing-record",
        ),
        pytest.param(
            [
                (
                    {
                        "question": "Check this route.",
                        "lookup": {
                            "kind": "journey",
                            "departure": "Unknown fixture departure station",
                            "arrival": "Colombo Fort",
                            "travel_date": "2026-11-16",
                        },
                    },
                    "clarify",
                ),
                ({"question": "How do I search by station name?"}, "search-direct-journeys"),
            ],
            id="unknown-station-then-guide",
        ),
        pytest.param(
            [
                (
                    {
                        "question": "Can you check an incident?",
                        "lookup": {"kind": "incident"},
                    },
                    "clarify",
                ),
                ({"question": "How can I report a disruption?"}, "report-disruption"),
                ({"question": "What does estimated arrival mean?"}, "interpret-delay-estimates"),
            ],
            id="incident-clarification-then-two-guide-topics",
        ),
        pytest.param(
            [
                ({"question": "Can I check direct alternatives?"}, "check-direct-alternatives"),
                ({"question": "Can I check alternative bus routes?"}, "unavailable"),
                ({"question": "Is the demo timetable fictional?"}, "demonstration-coverage"),
            ],
            id="rail-alternatives-then-bus-fallback",
        ),
        pytest.param(
            [
                ({"question": "What does estimated departure mean?"}, "interpret-delay-estimates"),
                ({"question": "Can you estimate the fare for my journey?"}, "unavailable"),
                ({"question": "How do I refresh journey results?"}, "interpret-delay-estimates"),
            ],
            id="estimates-then-fare-then-refresh",
        ),
        pytest.param(
            [
                ({"question": "Where can I search the live timetable?"}, "unavailable"),
                (
                    {"question": "Does the demo timetable cover the entire country?"},
                    "demonstration-coverage",
                ),
                (
                    {"question": "How do I search for a timetable journey?"},
                    "search-direct-journeys",
                ),
            ],
            id="live-fallback-then-demo-guidance",
        ),
    ],
)
def test_assistant_multi_turn_scenario(
    assistant_client: TestClient,
    turns: list[tuple[dict[str, object], str]],
) -> None:
    url = _create_conversation(assistant_client)
    saved_turns: list[dict[str, object]] = []

    for turn_number, (payload, expected) in enumerate(turns, start=1):
        response = assistant_client.post(f"{url}/turns", headers=ORIGIN, json=payload)
        assert response.status_code == 201, response.text
        turn = response.json()
        assert turn["turn_number"] == turn_number
        assert turn["question"] == payload["question"]

        answer = turn["answer"]
        if expected in {"clarify", "unavailable"}:
            assert answer["status"] == expected
            assert answer["citations"] == []
        else:
            assert answer["status"] == "answered"
            assert [citation["chunk_id"] for citation in answer["citations"]] == [expected]

        saved_turns.append(turn)
        history = assistant_client.get(url)
        assert history.status_code == 200, history.text
        assert history.json()["turns"] == saved_turns
