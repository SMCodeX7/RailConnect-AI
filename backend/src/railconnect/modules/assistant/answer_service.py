import re

from railconnect.modules.assistant.answer_schemas import (
    AssistantAnswer,
    AssistantQuestion,
    PolicyCitation,
)
from railconnect.modules.assistant.passenger_guide_v1 import PASSENGER_GUIDE_V1
from railconnect.modules.assistant.retrieval import WORD_PATTERN, search_policy

OUT_OF_SCOPE = re.compile(
    r"\b(?:fares?|prices?|tickets?|refunds?|insurance|platforms?|"
    r"seat availability|live gps|live timetables?|weather|buses|bus|"
    r"internet|broadband|private (?:notes|evidence)|staff member)\b"
)

TOPIC_TERMS = {
    "search-direct-journeys": (
        {"search", "find", "lookup"},
        {"journey", "journeys", "timetable", "train", "trains", "station", "stations"},
    ),
    "report-disruption": (
        {"report", "reports", "submit", "submitted", "notify", "tell"},
        {"disruption", "disruptions", "interruption", "observation", "pending"},
    ),
    "interpret-delay-estimates": (
        {"verified", "estimated", "estimate", "estimates", "refresh", "update"},
        {"delay", "delays", "arrival", "departure", "journey", "results"},
    ),
    "check-direct-alternatives": (
        {"check", "find", "direct", "show"},
        {"alternative", "alternatives"},
    ),
    "demonstration-coverage": (
        {"demo", "demonstration", "fictional", "coverage"},
        {"schedule", "schedules", "timetable", "data", "coverage"},
    ),
}

TOPIC_PHRASES = {
    "search-direct-journeys": (
        "travel date the day i board",
        "boarding date mean",
    ),
    "interpret-delay-estimates": (
        "different arrival times",
        "different departure times",
    ),
    "check-direct-alternatives": (
        "another direct service",
        "another train for the same station pair",
        "other direct services",
    ),
    "demonstration-coverage": (
        "shown for every date",
        "sample times",
        "outside the prepared dates",
    ),
}


def _unavailable() -> AssistantAnswer:
    return AssistantAnswer(
        status="unavailable",
        answer="The RailConnect passenger guide does not cover this question.",
        citations=[],
    )


def answer_policy_question(question: AssistantQuestion) -> AssistantAnswer:
    normalised = " ".join(WORD_PATTERN.findall(question.question.casefold()))
    if OUT_OF_SCOPE.search(normalised):
        return _unavailable()

    terms = set(normalised.split())
    if "look up" in normalised:
        terms.add("lookup")

    candidates = [
        chunk
        for chunk in PASSENGER_GUIDE_V1
        if all(terms & group for group in TOPIC_TERMS[chunk.chunk_id])
        or any(phrase in normalised for phrase in TOPIC_PHRASES.get(chunk.chunk_id, ()))
    ]
    matches = (
        candidates
        if len(candidates) == 1
        else search_policy(question.question, candidates, limit=1)
    )
    if not matches:
        return _unavailable()

    chunk = matches[0]
    return AssistantAnswer(
        status="answered",
        answer=chunk.text,
        citations=[
            PolicyCitation(
                source_id=chunk.source_id,
                source_version=chunk.source_version,
                chunk_id=chunk.chunk_id,
                title=chunk.title,
            )
        ],
    )
