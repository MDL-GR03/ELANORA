"""Helpers for matching researcher-proposed topic names to curated topics."""

import unicodedata
from collections.abc import Iterable
from typing import Protocol

TOPIC_SIMILARITY_THRESHOLD = 0.78


class NamedTopic(Protocol):
    """Minimal topic shape accepted by the matcher."""

    name: str


class SimilarResearchTopicError(ValueError):
    """Raised when a proposed new topic resembles a curated topic."""

    def __init__(self, topic: NamedTopic) -> None:
        self.topic = topic
        super().__init__(f'A similar research topic already exists: "{topic.name}"')


def normalize_topic_name(value: str) -> str:
    """Normalize spelling input for case, accents, punctuation, and spacing."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(
        "".join(
            character if character.isalnum() else " " for character in plain
        ).split()
    )


def find_similar_topic[TopicT: NamedTopic](
    proposed_name: str, topics: Iterable[TopicT]
) -> TopicT | None:
    """Return the closest topic only when it clears the duplicate threshold."""
    normalized_proposal = normalize_topic_name(proposed_name)
    if not normalized_proposal:
        return None
    scored = []
    for topic in topics:
        candidate = normalize_topic_name(topic.name)
        length = max(len(normalized_proposal), len(candidate))
        score = (
            1 - _edit_distance(normalized_proposal, candidate) / length if length else 1
        )
        scored.append((score, topic))
    if not scored:
        return None
    score, topic = max(scored, key=lambda item: item[0])
    return topic if score >= TOPIC_SIMILARITY_THRESHOLD else None


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def require_distinct_topic_name(
    proposed_name: str, topics: Iterable[NamedTopic]
) -> None:
    """Reject a new label until the user explicitly handles a close match."""
    similar = find_similar_topic(proposed_name, topics)
    if similar is not None:
        raise SimilarResearchTopicError(similar)
