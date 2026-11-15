import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from railconnect.modules.assistant.answer_schemas import AssistantQuestion, PolicyCitation
from railconnect.modules.assistant.answer_service import answer_policy_question
from railconnect.modules.assistant.passenger_guide_v1 import PASSENGER_GUIDE_V1

CASE_DIRECTORY = Path(__file__).resolve().parents[1] / "evaluation" / "assistant"
MINIMUM_FINAL_CASES = 60
HEADERS = ["id", "question", "expected_chunk_id"]


@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    expected_chunk_id: str


def read_cases(path: Path) -> list[Case]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADERS:
            raise ValueError(f"{path.name} must have these columns: {', '.join(HEADERS)}")

        cases = [
            Case(row["id"].strip(), row["question"].strip(), row["expected_chunk_id"].strip())
            for row in reader
            if None not in row and all(row.get(header) is not None for header in HEADERS)
        ]

    if not cases or any(not case.case_id or not case.question for case in cases):
        raise ValueError(f"{path.name} must contain cases with an ID and a question.")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError(f"{path.name} contains duplicate case IDs.")
    if len(question_set(cases)) != len(cases):
        raise ValueError(f"{path.name} contains duplicate questions.")

    return cases


def question_set(cases: list[Case]) -> set[str]:
    return {" ".join(case.question.casefold().split()) for case in cases}


def evaluate(cases: list[Case]) -> int:
    sources = {chunk.chunk_id: chunk for chunk in PASSENGER_GUIDE_V1}
    supported = retrieval_hits = answered = faithful = unavailable = declines = failures = 0

    for case in cases:
        expected = case.expected_chunk_id
        if expected and expected not in sources:
            raise ValueError(f"{case.case_id} references unknown chunk {expected!r}.")

        result = answer_policy_question(AssistantQuestion(question=case.question))

        citation = result.citations[0] if len(result.citations) == 1 else None
        cited_id = citation.chunk_id if isinstance(citation, PolicyCitation) else ""
        source = sources.get(cited_id)
        grounded = (
            result.status == "answered"
            and source is not None
            and isinstance(citation, PolicyCitation)
            and citation.source_id == source.source_id
            and citation.source_version == source.source_version
            and result.answer == source.text
        )
        answered += int(result.status == "answered")
        faithful += int(grounded)

        if expected:
            supported += 1
            correct_retrieval = result.status == "answered" and cited_id == expected
            retrieval_hits += int(correct_retrieval)
            passed = correct_retrieval and grounded
        else:
            unavailable += 1
            passed = result.status == "unavailable" and not result.citations
            declines += int(passed)

        if not passed:
            failures += 1
            expected_result = expected or "unavailable"
            actual_result = cited_id or result.status
            print(f"FAIL {case.case_id}: expected {expected_result}, got {actual_result}")

    print(f"Cases passed: {len(cases) - failures}/{len(cases)}")
    print(f"Expected excerpt retrieved: {retrieval_hits}/{supported}")
    print(f"Answers faithful to their cited excerpt: {faithful}/{answered}")
    print(f"Unsupported questions correctly declined: {declines}/{unavailable}")
    return int(failures > 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RailConnect passenger guide answers.")
    parser.add_argument("--split", choices=("tuning", "final"), required=True)
    args = parser.parse_args()

    try:
        cases = read_cases(CASE_DIRECTORY / f"policy-{args.split}.csv")
        if args.split == "final":
            tuning = read_cases(CASE_DIRECTORY / "policy-tuning.csv")
            if len(cases) < MINIMUM_FINAL_CASES:
                raise ValueError(f"The final set needs at least {MINIMUM_FINAL_CASES} cases.")
            if question_set(cases) & question_set(tuning):
                raise ValueError("Tuning and final questions must be separate.")

        print(f"Passenger guide evaluation: {args.split}")
        return evaluate(cases)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Evaluation error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
