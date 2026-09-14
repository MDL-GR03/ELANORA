from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from app.schema.requests.tier import ProjectBaselineTiersRequest, ResearchTopicRequest
from app.service.research_topics import (
    SimilarResearchTopicError,
    find_similar_topic,
    normalize_topic_name,
    require_distinct_topic_name,
)


@dataclass
class Topic:
    name: str


def test_topic_normalization_ignores_case_accents_punctuation_and_spacing():
    assert normalize_topic_name("  PROSÓDY---Analysis ") == "prosody analysis"


def test_small_researcher_typo_matches_existing_curated_topic():
    prosody = Topic("Prosody")

    assert find_similar_topic("prozody", [Topic("Gaze"), prosody]) is prosody


def test_distinct_topic_remains_a_new_suggestion():
    assert find_similar_topic("Turn taking", [Topic("Prosody"), Topic("Gaze")]) is None


def test_near_duplicate_cannot_be_created_without_explicitly_selecting_existing():
    with pytest.raises(SimilarResearchTopicError, match="Prosody") as caught:
        require_distinct_topic_name("prozody", [Topic("Prosody")])

    assert caught.value.topic.name == "Prosody"


def test_topic_request_strips_identifiers_at_the_input_boundary():
    request = ResearchTopicRequest(
        name="  Prosody  ", tier_names=["  intonation  "], allow_new_tiers=False
    )

    assert request.name == "Prosody"
    assert request.tier_names == ["intonation"]


@pytest.mark.parametrize(
    "request_factory",
    [
        lambda: ResearchTopicRequest(name="   ", tier_names=["intonation"]),
        lambda: ResearchTopicRequest(name="Prosody", tier_names=["   "]),
        lambda: ProjectBaselineTiersRequest(tier_names=["   "]),
    ],
)
def test_blank_topic_identifiers_are_rejected_by_request_validation(request_factory):
    with pytest.raises(ValidationError):
        request_factory()
