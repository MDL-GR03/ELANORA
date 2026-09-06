"""SQLAlchemy models package.

This module imports all models in the correct order to avoid circular imports.
Models are imported based on their dependencies, with base models first.
"""

# Import enums first
from .accepted_value import AcceptedValue
from .address import Address
from .annotation import Annotation

# Base models with no dependencies
from .annotation_standard import AnnotationStandard
from .annotation_value import AnnotationValue

# Association tables (import last)
from .association import (
    ElanFileToMedia,
    ElanFileToTier,
    ProjectAnnotStandard,
    ProjectCapabilityGrant,
    UserToProject,
)
from .audit_event import AuditEvent, OutboxEvent

# Models with single dependencies
from .city import City
from .component_accepted_value import ComponentAcceptedValue
from .component_template import ComponentTemplate
from .country import Country
from .eaf_ingestion_attempt import EafIngestionAttempt
from .eaf_revision import EafRevision
from .effective_naming_standard import EffectiveNamingStandard

# Models with dependencies on user/project
from .elan_file import ElanFile
from .elan_file_media import ElanFileMedia
from .enums import (
    InvitationStatus,
    ProjectCapability,
    ProjectPermission,
    ProtocolVersionStatus,
    ReviewCaseState,
    Severity,
    Status,
    Type,
    UserRole,
    ValidationOutcome,
    ValidationSeverity,
)
from .file_content import FileContent
from .file_type import FileType
from .instance import Instance
from .instance_asset import InstanceAsset
from .invitation import Invitation
from .notification import Notification
from .notification_preference import NotificationPreference
from .pending_upload import PendingUpload

# Project model (depends on instance)
from .project import Project
from .project_file_type import ProjectFileType
from .project_location_file_type import ProjectLocationFileType
from .project_naming_standard import ProjectNamingStandard
from .project_sync_operation import ProjectSyncOperation
from .protocol import (
    ProjectComplianceScan,
    ProjectComplianceScanFile,
    Protocol,
    ProtocolValidationIssue,
    ProtocolVersion,
    ProtocolVersionArchive,
    ValidationRun,
    ValidatorRelease,
)
from .review import ReviewCase, ReviewComment
from .standard_component import StandardComponent

# Tier and annotation models
from .tier import Tier
from .tier_group import TierGroup
from .tier_section import TierSection

# User model (depends on address)
from .user import User

__all__ = [
    "AcceptedValue",
    "Address",
    "Annotation",
    "AnnotationStandard",
    "AnnotationValue",
    "AuditEvent",
    "City",
    "ComponentAcceptedValue",
    "ComponentTemplate",
    "Country",
    "EafIngestionAttempt",
    "EafRevision",
    "EffectiveNamingStandard",
    "ElanFile",
    "ElanFileMedia",
    "ElanFileToMedia",
    "ElanFileToTier",
    "FileContent",
    "FileType",
    "Instance",
    "InstanceAsset",
    "Invitation",
    "InvitationStatus",
    "Notification",
    "NotificationPreference",
    "OutboxEvent",
    "PendingUpload",
    "Project",
    "ProjectAnnotStandard",
    "ProjectCapability",
    "ProjectCapabilityGrant",
    "ProjectComplianceScan",
    "ProjectComplianceScanFile",
    "ProjectFileType",
    "ProjectLocationFileType",
    "ProjectNamingStandard",
    "ProjectPermission",
    "ProjectSyncOperation",
    "Protocol",
    "ProtocolValidationIssue",
    "ProtocolVersion",
    "ProtocolVersionArchive",
    "ProtocolVersionStatus",
    "ReviewCase",
    "ReviewCaseState",
    "ReviewComment",
    "Severity",
    "StandardComponent",
    "Status",
    "Tier",
    "TierGroup",
    "TierSection",
    "Type",
    "User",
    "UserRole",
    "UserToProject",
    "ValidationOutcome",
    "ValidationRun",
    "ValidationSeverity",
    "ValidatorRelease",
]
