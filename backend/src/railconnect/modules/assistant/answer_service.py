from railconnect.modules.assistant.answer_schemas import (
    AssistantAnswer,
    AssistantQuestion,
    PolicyCitation,
)
from railconnect.modules.assistant.passenger_guide_v1 import PASSENGER_GUIDE_V1
from railconnect.modules.assistant.retrieval import WORD_PATTERN, search_policy

TOPIC_TERMS = {
    "search-direct-journeys": (
        {"search", "find"},
        {"journey", "journeys", "timetable", "station", "stations"},
    ),
    "report-disruption": (
        {"report", "reports", "submit", "submitted"},
        {"disruption", "disruptions", "observation", "pending"},
    ),
    "interpret-delay-estimates": (
        {"verified", "estimated", "estimate", "estimates", "refresh"},
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


def answer_policy_question(question: AssistantQuestion) -> AssistantAnswer:
    terms = set(WORD_PATTERN.findall(question.question.casefold()))
    candidates = [
        chunk
        for chunk in PASSENGER_GUIDE_V1
        if all(terms & group for group in TOPIC_TERMS[chunk.chunk_id])
    ]
    matches = search_policy(question.question, candidates, limit=1)

    if not matches:
        return AssistantAnswer(
            status="unavailable",
            answer="The RailConnect passenger guide does not cover this question.",
            citations=[],
        )

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
