"""Proposing rules from what a project's accepted corpus already contains."""

import asyncio
from collections import Counter, defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.elan.validation import EafValidationError, validate_eaf
from app.model.project import Project
from app.schema.protocol import (
    CorpusProtocolSuggestionResponse,
    ProtocolRules,
    ProtocolTierSuggestion,
    ProtocolVocabularySuggestion,
)
from app.service.protocol_shared import latest_project_revisions

FULL_COVERAGE_PERCENT = 100.0


async def suggest_protocol_from_corpus(
    db: AsyncSession, project: Project
) -> CorpusProtocolSuggestionResponse:
    """Infer conservative, evidence-backed rules from latest accepted revisions."""
    revisions = await latest_project_revisions(db, project)
    tier_counts: Counter[str] = Counter()
    tier_parents: dict[str, Counter[str]] = defaultdict(Counter)
    tier_types: dict[str, Counter[str]] = defaultdict(Counter)
    vocabulary_counts: Counter[str] = Counter()
    media_type_counts: Counter[str] = Counter()
    files_with_media = 0
    skipped_files: list[str] = []
    analyzed_files = 0

    for revision in revisions:
        try:
            root = await asyncio.to_thread(validate_eaf, revision.raw_xml)
        except EafValidationError:
            skipped_files.append(revision.elan_file.filename)
            continue
        analyzed_files += 1
        file_tiers: set[str] = set()
        for tier in root.findall("TIER"):
            tier_id = tier.get("TIER_ID")
            if not tier_id or tier_id in file_tiers:
                continue
            file_tiers.add(tier_id)
            if parent := tier.get("PARENT_REF"):
                tier_parents[tier_id][parent] += 1
            if linguistic_type := tier.get("LINGUISTIC_TYPE_REF"):
                tier_types[tier_id][linguistic_type] += 1
        tier_counts.update(file_tiers)
        vocabulary_counts.update(
            {
                vocabulary_id
                for vocabulary in root.findall("CONTROLLED_VOCABULARY")
                if (vocabulary_id := vocabulary.get("CV_ID"))
            }
        )
        descriptors = root.findall("HEADER/MEDIA_DESCRIPTOR")
        if descriptors:
            files_with_media += 1
        media_type_counts.update(
            {
                mime_type
                for descriptor in descriptors
                if (mime_type := descriptor.get("MIME_TYPE"))
            }
        )

    def consensus(
        variants: Counter[str], occurrences: int
    ) -> tuple[str | None, float | None]:
        if not variants or not occurrences:
            return None, None
        value, count = variants.most_common(1)[0]
        return value, round(count * 100 / occurrences, 1)

    tier_suggestions: list[ProtocolTierSuggestion] = []
    for tier_id, count in tier_counts.most_common():
        parent, parent_consistency = consensus(tier_parents[tier_id], count)
        linguistic_type, type_consistency = consensus(tier_types[tier_id], count)
        tier_suggestions.append(
            ProtocolTierSuggestion(
                tier_id=tier_id,
                occurrence_count=count,
                coverage_percent=round(count * 100 / analyzed_files, 1),
                suggested_required=count == analyzed_files,
                parent_ref=parent,
                parent_consistency_percent=parent_consistency,
                parent_variants=dict(tier_parents[tier_id]),
                linguistic_type_ref=linguistic_type,
                linguistic_type_consistency_percent=type_consistency,
                linguistic_type_variants=dict(tier_types[tier_id]),
            )
        )
    vocabulary_suggestions = (
        [
            ProtocolVocabularySuggestion(
                vocabulary_id=vocabulary_id,
                occurrence_count=count,
                coverage_percent=round(count * 100 / analyzed_files, 1),
                suggested_required=count == analyzed_files,
            )
            for vocabulary_id, count in vocabulary_counts.most_common()
        ]
        if analyzed_files
        else []
    )
    required_tiers = [
        item.tier_id for item in tier_suggestions if item.suggested_required
    ]
    required_set = set(required_tiers)
    proposed_rules = ProtocolRules(
        required_tiers=required_tiers,
        tier_parents={
            item.tier_id: item.parent_ref
            for item in tier_suggestions
            if item.suggested_required
            and item.parent_ref in required_set
            and item.parent_consistency_percent == FULL_COVERAGE_PERCENT
        },
        tier_linguistic_types={
            item.tier_id: item.linguistic_type_ref
            for item in tier_suggestions
            if item.suggested_required
            and item.linguistic_type_ref is not None
            and item.linguistic_type_consistency_percent == FULL_COVERAGE_PERCENT
        },
        required_controlled_vocabularies=[
            item.vocabulary_id
            for item in vocabulary_suggestions
            if item.suggested_required
        ],
        media_required=analyzed_files > 0 and files_with_media == analyzed_files,
        allowed_media_mime_types=sorted(media_type_counts),
    )
    return CorpusProtocolSuggestionResponse(
        total_files=len(revisions),
        analyzed_files=analyzed_files,
        skipped_files=skipped_files,
        tier_suggestions=tier_suggestions,
        vocabulary_suggestions=vocabulary_suggestions,
        media_type_counts=dict(media_type_counts),
        files_with_media=files_with_media,
        proposed_rules=proposed_rules,
    )
