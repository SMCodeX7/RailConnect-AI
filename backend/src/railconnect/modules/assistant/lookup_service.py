from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from psycopg.errors import QueryCanceled
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from railconnect.modules.assistant.answer_schemas import (
    AssistantAnswer,
    AssistantQuestion,
    IncidentLookup,
    JourneyLookup,
    PolicyCitation,
    RecordCitation,
)
from railconnect.modules.assistant.answer_service import answer_policy_question
from railconnect.modules.incidents.errors import IncidentNotFoundError
from railconnect.modules.incidents.public_service import get_public_incident
from railconnect.modules.journeys.errors import InvalidStationSelectionError
from railconnect.modules.journeys.schemas import JourneySearchQuery
from railconnect.modules.journeys.service import search_journeys
from railconnect.modules.stations.models import Station

COLOMBO = ZoneInfo("Asia/Colombo")
MAX_JOURNEYS = 3


def _clarify(message: str) -> AssistantAnswer:
    return AssistantAnswer(status="clarify", answer=message, citations=[])


def _unavailable(message: str) -> AssistantAnswer:
    return AssistantAnswer(status="unavailable", answer=message, citations=[])


def _colombo_time(value: datetime) -> str:
    return value.astimezone(COLOMBO).strftime("%Y-%m-%d %H:%M")


def _station_matches(session: Session, name: str) -> list[Station]:
    if "\x00" in name:
        return []

    return list(
        session.scalars(
            select(Station)
            .where(
                Station.is_active.is_(True),
                or_(func.lower(Station.name) == name.lower(), Station.code == name.upper()),
            )
            .order_by(Station.code)
            .limit(4)
        )
    )


def _station_prompt(label: str, matches: list[Station]) -> str:
    if not matches:
        return f"I couldn't find that {label} station. Enter its exact name or station code."

    options = ", ".join(f"{station.name} ({station.code})" for station in matches)
    return f"More than one {label} station matches. Choose a station code: {options}."


def _journey_answer(session: Session, lookup: JourneyLookup) -> AssistantAnswer:
    if lookup.departure is None or lookup.arrival is None or lookup.travel_date is None:
        return _clarify("Enter the departure station, arrival station and boarding date.")

    departures = _station_matches(session, lookup.departure)
    if len(departures) != 1:
        return _clarify(_station_prompt("departure", departures))

    arrivals = _station_matches(session, lookup.arrival)
    if len(arrivals) != 1:
        return _clarify(_station_prompt("arrival", arrivals))

    departure, arrival = departures[0], arrivals[0]
    if departure.id == arrival.id:
        return _clarify("Choose different departure and arrival stations.")

    try:
        result = search_journeys(
            session,
            JourneySearchQuery(
                departure_station_id=departure.id,
                arrival_station_id=arrival.id,
                travel_date=lookup.travel_date,
                limit=MAX_JOURNEYS,
            ),
        )
    except InvalidStationSelectionError:
        return _clarify("One of the stations is unavailable. Choose the stations again.")

    if not result.items:
        return _unavailable(
            "No prepared direct journey matched those stations and date in RailConnect."
        )

    lines = ["RailConnect demonstration timetable · Sri Lanka time."]
    citations: list[PolicyCitation | RecordCitation] = []
    for journey in result.items:
        line = (
            f"{journey.service_name}: scheduled departure {_colombo_time(journey.departure_at)}, "
            f"scheduled arrival {_colombo_time(journey.arrival_at)}."
        )
        if journey.run_status == "restricted":
            line += " The run is restricted. Review journey details before choosing it."

        disruption = journey.disruption
        if disruption is not None:
            if disruption.estimated_departure_at is not None:
                line += f" Estimated departure {_colombo_time(disruption.estimated_departure_at)}."
            if disruption.estimated_arrival_at is not None:
                line += f" Estimated arrival {_colombo_time(disruption.estimated_arrival_at)}."

        lines.append(line)
        params = urlencode(
            {
                "departure_stop_sequence": journey.departure_stop_sequence,
                "arrival_stop_sequence": journey.arrival_stop_sequence,
            }
        )
        citations.append(
            RecordCitation(
                kind="journey",
                title=journey.service_name,
                href=f"/api/v1/journeys/{journey.run_id}?{params}",
                record_version=journey.run_version,
            )
        )

    if result.total > len(result.items):
        lines.append(f"Showing {len(result.items)} of {result.total} matching journeys.")

    return AssistantAnswer(status="answered", answer="\n".join(lines), citations=citations)


def _incident_answer(session: Session, lookup: IncidentLookup) -> AssistantAnswer:
    if lookup.incident_id is None:
        return _clarify("Enter the public incident ID you want to look up.")

    try:
        incident = get_public_incident(session, lookup.incident_id)
    except IncidentNotFoundError:
        return _unavailable("No public verified incident matches that ID.")

    answer = (
        f"RailConnect verified incident record. Status: {incident.status}. "
        f"Recorded impact: {incident.impact_kind}. {incident.public_summary}\n"
        f"Recorded window: {_colombo_time(incident.effective_from)} to "
        f"{_colombo_time(incident.effective_until)} Sri Lanka time. "
        f"Verified at {_colombo_time(incident.verified_at)} Sri Lanka time."
    )
    if incident.resolution_effective_at is not None:
        answer += (
            f" Resolution effective at {_colombo_time(incident.resolution_effective_at)} "
            "Sri Lanka time."
        )

    return AssistantAnswer(
        status="answered",
        answer=answer,
        citations=[
            RecordCitation(
                kind="incident",
                title="Verified incident record",
                href=f"/api/v1/incidents/{incident.incident_id}",
                record_version=incident.incident_version,
                revision_id=incident.revision_id,
            )
        ],
    )


def answer_assistant_question(session: Session, question: AssistantQuestion) -> AssistantAnswer:
    lookup = question.lookup
    if lookup is None:
        return answer_policy_question(question)

    try:
        with session.begin_nested():
            session.execute(text("SET LOCAL statement_timeout = '2s'"))
            if isinstance(lookup, JourneyLookup):
                return _journey_answer(session, lookup)
            return _incident_answer(session, lookup)
    except DBAPIError as error:
        if not isinstance(error.orig, QueryCanceled):
            raise
        return _unavailable("The lookup took too long. Please try again.")
