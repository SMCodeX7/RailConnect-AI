import pytest
from pydantic import ValidationError

from railconnect.modules.assistant.answer_schemas import AssistantQuestion
from railconnect.modules.assistant.answer_service import answer_policy_question
from railconnect.modules.assistant.passenger_guide_v1 import PASSENGER_GUIDE_V1


@pytest.mark.parametrize(
    ("question", "expected_chunk_id"),
    [
        ("How do I report a disruption?", "report-disruption"),
        ("How do I check direct alternatives?", "check-direct-alternatives"),
        ("What does estimated arrival mean?", "interpret-delay-estimates"),
    ],
)
def test_policy_answer_quotes_versioned_evidence(
    question: str,
    expected_chunk_id: str,
) -> None:
    answer = answer_policy_question(AssistantQuestion(question=question))
    source = next(chunk for chunk in PASSENGER_GUIDE_V1 if chunk.chunk_id == expected_chunk_id)

    assert answer.status == "answered"
    assert answer.answer == source.text
    assert len(answer.citations) == 1
    assert answer.citations[0].model_dump() == {
        "source_id": source.source_id,
        "source_version": source.source_version,
        "chunk_id": source.chunk_id,
        "title": source.title,
    }


@pytest.mark.parametrize(
    "question",
    ["What is the ticket price for my journey?", "Is my train running right now?"],
)
def test_policy_answer_declines_questions_without_guide_evidence(question: str) -> None:
    answer = answer_policy_question(AssistantQuestion(question=question))

    assert answer.status == "unavailable"
    assert answer.citations == []


@pytest.mark.parametrize("question", ["   ", "x" * 501])
def test_question_rejects_input_outside_length_bounds(question: str) -> None:
    with pytest.raises(ValidationError):
        AssistantQuestion(question=question)
