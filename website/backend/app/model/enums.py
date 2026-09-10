"""Shared enums for the application.

This module contains all enum definitions used across models.
"""

from enum import StrEnum


class UserRole(StrEnum):
    """Enum for user roles."""

    ADMIN = "admin"
    PUBLIC = "public"


class ProjectPermission(StrEnum):
    """Enumeration for project permissions."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        return None


class ProjectCapability(StrEnum):
    """Optional project capabilities independent of the access hierarchy."""

    MANAGE_PROTOCOLS = "manage_protocols"


class ProtocolVersionStatus(StrEnum):
    """Lifecycle states for an immutable protocol snapshot."""

    DRAFT = "draft"
    PUBLISHED = "published"


class ValidationOutcome(StrEnum):
    """Persisted result of validating one immutable EAF revision."""

    PASSED = "passed"
    FAILED = "failed"


class ValidationSeverity(StrEnum):
    """Severity attached to a protocol validation issue."""

    ERROR = "error"
    WARNING = "warning"


class InvitationStatus(StrEnum):
    """Enumeration for invitation status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Type(StrEnum):
    """Enumeration for conflict types."""

    # Original ELAN conflict types
    ANNOTATION_OVERLAP = "annotation_overlap"
    TIER_MISMATCH = "tier_mismatch"
    VALUE_DIFFERENCE = "value_difference"
    STRUCTURAL = "structural"
    OTHER = "other"

    # Upload workflow types
    PENDING_UPLOAD = "pending_upload"
    UPLOAD_NEW_FILES_ONLY = "upload_new_files_only"
    UPLOAD_WITH_MODIFICATIONS = "upload_with_modifications"
    UPLOAD_WITH_DELETIONS = "upload_with_deletions"
    UPLOAD_MIXED_CHANGES = "upload_mixed_changes"


class Severity(StrEnum):
    """Enumeration for conflict severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Status(StrEnum):
    """Enumeration for conflict status."""

    PENDING_ADMIN_APPROVAL = "pending_admin_approval"
    READY_TO_MERGE = "ready_to_merge"
    NEEDS_RESOLUTION = "needs_resolution"
    BEING_REVIEWED = "being_reviewed"
    # Final statuses
    RESOLVED = "resolved"  # Successfully merged
    NO_CHANGES = "no_changes"  # Reviewed successfully; project content unchanged
    DISMISSED = "dismissed"  # Rejected/cancelled


class ReviewCaseState(StrEnum):
    """Lifecycle of a researcher-facing contribution review case."""

    OPEN = "open"
    CHANGES_REQUESTED = "changes_requested"
    RESUBMITTED = "resubmitted"
    RESOLVED = "resolved"
    CLOSED = "closed"
