"""Typed API contracts for protocol governance and validation evidence."""

import uuid
from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.filename_standard import FilenameComponent, compile_standard
from app.model.enums import (
    ProtocolVersionStatus,
    ValidationOutcome,
    ValidationSeverity,
)

ConstraintStereotype = Literal[
    "none",
    "Time_Subdivision",
    "Included_In",
    "Symbolic_Subdivision",
    "Symbolic_Association",
]


class FilenameComponentRule(BaseModel):
    """One component of a frozen filename standard."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    # Empty means any non-empty text.
    regex: str = Field(default="", max_length=255)
    accepted_values: list[str] = Field(default_factory=list, max_length=500)


class FilenameStandardRule(BaseModel):
    """A naming standard copied into a protocol, independent of later edits."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    pattern: str = Field(min_length=1, max_length=255)
    components: list[FilenameComponentRule] = Field(default_factory=list, max_length=50)

    def matcher_components(self) -> tuple[FilenameComponent, ...]:
        return tuple(
            FilenameComponent(
                name=component.name,
                regex=component.regex,
                accepted_values=tuple(component.accepted_values),
            )
            for component in self.components
        )

    @model_validator(mode="after")
    def standard_is_usable(self) -> "FilenameStandardRule":
        """Refuse a standard that could not judge any filename."""
        compile_standard(self.pattern, self.matcher_components())
        return self


class ProtocolRules(BaseModel):
    """First versioned rules supported by the deterministic validator."""

    model_config = ConfigDict(extra="forbid")

    required_tiers: list[str] = Field(default_factory=list, max_length=500)
    tier_parents: dict[str, str] = Field(default_factory=dict)
    tier_linguistic_types: dict[str, str] = Field(default_factory=dict)
    required_controlled_vocabularies: list[str] = Field(
        default_factory=list, max_length=500
    )
    media_required: bool = False
    allowed_media_mime_types: list[str] = Field(default_factory=list, max_length=100)
    # Vocabulary: annotations on these tiers must use an entry of the controlled
    # vocabulary named by the tier's linguistic type.
    vocabulary_tiers: list[str] = Field(default_factory=list, max_length=500)
    # Vocabulary: every entry needs a value in each listed language.
    vocabulary_languages: dict[str, list[str]] = Field(default_factory=dict)
    # Tier metadata.
    participant_tiers: list[str] = Field(default_factory=list, max_length=500)
    annotator_tiers: list[str] = Field(default_factory=list, max_length=500)
    tier_languages: dict[str, str] = Field(default_factory=dict)
    # Completeness.
    non_empty_tiers: list[str] = Field(default_factory=list, max_length=500)
    time_aligned_tiers: list[str] = Field(default_factory=list, max_length=500)
    # Linguistic-type constraint stereotypes; "none" means an unconstrained type.
    linguistic_type_constraints: dict[str, ConstraintStereotype] = Field(
        default_factory=dict
    )
    filename_standard: FilenameStandardRule | None = None
    # Rules absent here are errors, which keeps every protocol published before
    # severities existed behaving exactly as it did.
    severities: dict[str, ValidationSeverity] = Field(default_factory=dict)

    @classmethod
    def rule_keys(cls) -> frozenset[str]:
        """Names of the rule families that a severity can be attached to."""
        return frozenset(cls.model_fields) - {"severities"}

    def severity_of(self, rule_key: str) -> ValidationSeverity:
        """Severity of a rule's findings; errors unless marked as a warning."""
        return self.severities.get(rule_key, ValidationSeverity.ERROR)

    @field_validator(
        "required_tiers",
        "required_controlled_vocabularies",
        "allowed_media_mime_types",
        "vocabulary_tiers",
        "participant_tiers",
        "annotator_tiers",
        "non_empty_tiers",
        "time_aligned_tiers",
    )
    @classmethod
    def normalize_required_tiers(cls, values: list[str]) -> list[str]:
        """Reject empty identifiers and create one canonical ordered set."""
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("required tier identifiers cannot be empty")
        return sorted(set(normalized))

    @field_validator("vocabulary_languages")
    @classmethod
    def normalize_vocabulary_languages(
        cls, values: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Canonical ordering; every vocabulary names at least one language."""
        normalized: dict[str, list[str]] = {}
        for vocabulary_id, languages in values.items():
            cleaned = sorted({language.strip() for language in languages})
            if not vocabulary_id.strip() or not cleaned or "" in cleaned:
                raise ValueError(
                    "vocabulary languages need a vocabulary and non-empty languages"
                )
            normalized[vocabulary_id.strip()] = cleaned
        return dict(sorted(normalized.items()))

    @field_validator("linguistic_type_constraints")
    @classmethod
    def normalize_type_constraints(
        cls, values: dict[str, ConstraintStereotype]
    ) -> dict[str, ConstraintStereotype]:
        """Reject empty linguistic type identifiers."""
        normalized = {key.strip(): value for key, value in values.items()}
        if any(not key for key in normalized):
            raise ValueError("linguistic type identifiers cannot be empty")
        return cast(dict[str, ConstraintStereotype], dict(sorted(normalized.items())))

    @field_validator("tier_parents", "tier_linguistic_types", "tier_languages")
    @classmethod
    def normalize_tier_mappings(cls, values: dict[str, str]) -> dict[str, str]:
        """Normalize tier requirements while preserving explicit relationships."""
        normalized = {key.strip(): value.strip() for key, value in values.items()}
        if any(not key or not value for key, value in normalized.items()):
            raise ValueError("tier identifiers and required values cannot be empty")
        return dict(sorted(normalized.items()))

    @field_validator("severities")
    @classmethod
    def severities_name_known_rules(
        cls, values: dict[str, ValidationSeverity]
    ) -> dict[str, ValidationSeverity]:
        """Reject severities for rules that do not exist."""
        unknown = set(values) - cls.rule_keys()
        if unknown:
            raise ValueError(
                "severities refer to unknown rules: " + ", ".join(sorted(unknown))
            )
        return dict(sorted(values.items()))

    @model_validator(mode="after")
    def mapped_tiers_are_required(self) -> "ProtocolRules":
        """Make every tier carrying a relationship rule explicitly required."""
        # A rule on an optional tier would pass silently whenever it is absent.
        mapped = (
            set(self.tier_parents)
            | set(self.tier_linguistic_types)
            | set(self.tier_languages)
            | set(self.vocabulary_tiers)
            | set(self.participant_tiers)
            | set(self.annotator_tiers)
            | set(self.non_empty_tiers)
            | set(self.time_aligned_tiers)
        )
        missing = mapped - set(self.required_tiers)
        if missing:
            raise ValueError(
                "tiers with tier rules must also be required: "
                + ", ".join(sorted(missing))
            )
        vocabularies = set(self.vocabulary_languages) - set(
            self.required_controlled_vocabularies
        )
        if vocabularies:
            raise ValueError(
                "vocabularies with language rules must also be required: "
                + ", ".join(sorted(vocabularies))
            )
        required = set(self.required_tiers)
        unknown_parents = set(self.tier_parents.values()) - required
        if unknown_parents:
            raise ValueError(
                "parent tiers must also be required: "
                + ", ".join(sorted(unknown_parents))
            )
        for tier_id in self.tier_parents:
            visited = {tier_id}
            ancestor = self.tier_parents.get(tier_id)
            while ancestor is not None:
                if ancestor in visited:
                    raise ValueError("tier parent relationships cannot contain cycles")
                visited.add(ancestor)
                ancestor = self.tier_parents.get(ancestor)
        return self


class CreateProtocolRequest(BaseModel):
    """Create a stable protocol and its first draft."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=4000)
    rules: ProtocolRules = Field(default_factory=ProtocolRules)


class CreateProtocolVersionRequest(BaseModel):
    """Create the next editable draft from explicit rules."""

    rules: ProtocolRules


class UpdateProtocolDraftRequest(BaseModel):
    """Replace all rules in an unpublished draft."""

    rules: ProtocolRules


class ProtocolTierSuggestion(BaseModel):
    """Observed use of one tier across the latest project revisions."""

    tier_id: str
    occurrence_count: int
    coverage_percent: float
    suggested_required: bool
    parent_ref: str | None = None
    parent_consistency_percent: float | None = None
    parent_variants: dict[str, int] = Field(default_factory=dict)
    linguistic_type_ref: str | None = None
    linguistic_type_consistency_percent: float | None = None
    linguistic_type_variants: dict[str, int] = Field(default_factory=dict)


class ProtocolVocabularySuggestion(BaseModel):
    """Observed use of one controlled vocabulary across the corpus."""

    vocabulary_id: str
    occurrence_count: int
    coverage_percent: float
    suggested_required: bool


class CorpusProtocolSuggestionResponse(BaseModel):
    """Advisory protocol evidence inferred from immutable EAF revisions."""

    total_files: int
    analyzed_files: int
    skipped_files: list[str] = Field(default_factory=list)
    tier_suggestions: list[ProtocolTierSuggestion] = Field(default_factory=list)
    vocabulary_suggestions: list[ProtocolVocabularySuggestion] = Field(
        default_factory=list
    )
    media_type_counts: dict[str, int] = Field(default_factory=dict)
    files_with_media: int
    proposed_rules: ProtocolRules


class ArchiveProtocolVersionRequest(BaseModel):
    """Explain why a published version should no longer be selected."""

    reason: str | None = Field(default=None, max_length=2000)


class ProtocolVersionResponse(BaseModel):
    """Protocol version metadata and its complete rules snapshot."""

    model_config = ConfigDict(from_attributes=True)

    protocol_version_id: uuid.UUID
    protocol_id: uuid.UUID
    version_number: int
    status: ProtocolVersionStatus
    rules: dict[str, object]
    rules_sha256: str | None
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None = None
    archive_reason: str | None = None


class ProtocolResponse(BaseModel):
    """Stable protocol identity returned with its versions."""

    model_config = ConfigDict(from_attributes=True)

    protocol_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    versions: list[ProtocolVersionResponse]


class ValidationIssueResponse(BaseModel):
    """One persisted, machine-readable protocol violation."""

    model_config = ConfigDict(from_attributes=True)

    validation_issue_id: uuid.UUID
    issue_number: int
    code: str
    severity: ValidationSeverity
    location: str
    message: str
    rule_key: str | None


class ValidationRunResponse(BaseModel):
    """Immutable evidence returned after revision validation."""

    model_config = ConfigDict(from_attributes=True)

    validation_run_id: uuid.UUID
    revision_id: uuid.UUID
    protocol_version_id: uuid.UUID
    validator_release_id: uuid.UUID
    outcome: ValidationOutcome
    created_at: datetime
    issues: list[ValidationIssueResponse]


class ComplianceScanFileResponse(BaseModel):
    """One latest project file and its immutable validation result."""

    scan_file_id: uuid.UUID
    elan_id: int
    revision_id: uuid.UUID
    filename: str
    outcome: ValidationOutcome
    validation_run_id: uuid.UUID
    issues: list[ValidationIssueResponse]


class ComplianceScanResponse(BaseModel):
    """A complete, reproducible project compliance snapshot."""

    scan_id: uuid.UUID
    project_id: int
    protocol_version_id: uuid.UUID
    protocol_name: str
    protocol_version_number: int
    status: str
    trigger: str
    total_files: int
    passed_files: int
    failed_files: int
    started_at: datetime
    completed_at: datetime | None
    error_summary: str | None
    files: list[ComplianceScanFileResponse]


class CapabilityGrantResponse(BaseModel):
    """Confirmation of one delegated project capability."""

    project_id: int
    user_id: int
    capability: str
