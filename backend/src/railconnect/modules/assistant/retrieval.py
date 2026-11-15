import re
from collections.abc import Iterable
from dataclasses import dataclass

WORD_PATTERN = re.compile(r"[^\W_]+")
COMMON_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "can",
        "do",
        "for",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "where",
        "with",
    }
)


@dataclass(frozen=True)
class PolicyChunk:
    source_id: str
    source_version: str
    chunk_id: str
    title: str
    text: str


def _terms(text: str) -> set[str]:
    return set(WORD_PATTERN.findall(text.casefold())) - COMMON_WORDS


def search_policy(
    question: str,
    chunks: Iterable[PolicyChunk],
    *,
    limit: int = 3,
) -> list[PolicyChunk]:
    if not 1 <= limit <= 5:
        raise ValueError("Policy search limit must be between 1 and 5.")

    question_terms = _terms(question)
    if not question_terms:
        return []

    matches: list[tuple[int, int, PolicyChunk]] = []

    for chunk in chunks:
        title_terms = _terms(chunk.title)
        matched = question_terms & (title_terms | _terms(chunk.text))
        if matched:
            matches.append((len(matched), len(matched & title_terms), chunk))

    matches.sort(
        key=lambda match: (
            -match[0],
            -match[1],
            match[2].source_id,
            match[2].source_version,
            match[2].chunk_id,
        )
    )
    return [chunk for _, _, chunk in matches[:limit]]
