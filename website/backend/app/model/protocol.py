"""Versioned institutional protocols and immutable validation evidence."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.model.enums import (
    ProtocolVersionStatus,
    ValidationOutcome,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from app.model.eaf_revision import EafRevision
    from app.model.elan_file import ElanFile
    from app.model.instance import Instance
    from app.model.project import Project
    from app.model.user import User


class Protocol(Base):
    """Stable identity for an institution-owned annotation protocol."""

    __tablename__ = "PROTOCOL"
    __table_args__ = (
        UniqueConstraint("instance_id", "name", name="uq_protocol_instance_name"),
    )

    protocol_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("INSTANCE.instance_id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    instance: Mapped["Instance"] = relationship("Instance")
    creator: Mapped["User | None"] = relationship("User")
    versions: Mapped[list["ProtocolVersion"]] = relationship(
        "ProtocolVersion", back_populates="protocol", cascade="all, delete-orphan"
    )


class ProtocolVersion(Base):
    """A draft or immutable published protocol rules snapshot."""

    __tablename__ = "PROTOCOL_VERSION"
    __table_args__ = (
        UniqueConstraint(
            "protocol_id", "version_number", name="uq_protocol_version_number"
        ),
        CheckConstraint("version_number > 0", name="ck_protocol_version_positive"),
        CheckConstraint(
            "status IN ('draft', 'published')", name="ck_protocol_version_status"
        ),
        CheckConstraint(
            "rules_sha256 IS NULL OR length(rules_sha256) = 64",
            name="ck_protocol_version_sha256",
        ),
        CheckConstraint(
            "(status = 'draft' AND rules_sha256 IS NULL "
            "AND published_by IS NULL AND published_at IS NULL) OR "
            "(status = 'published' AND rules_sha256 IS NOT NULL "
            "AND published_by IS NOT NULL AND published_at IS NOT NULL)",
            name="ck_protocol_version_lifecycle",
        ),
    )

    protocol_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROTOCOL.protocol_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ProtocolVersionStatus] = mapped_column(
        String(20), nullable=False, default=ProtocolVersionStatus.DRAFT
    )
    rules: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    rules_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    published_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    protocol: Mapped["Protocol"] = relationship("Protocol", back_populates="versions")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    publisher: Mapped["User | None"] = relationship("User", foreign_keys=[published_by])
    archive: Mapped["ProtocolVersionArchive | None"] = relationship(
        "ProtocolVersionArchive",
        back_populates="protocol_version",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )

    @property
    def archived_at(self) -> datetime | None:
        return self.archive.archived_at if self.archive else None

    @property
    def archive_reason(self) -> str | None:
        return self.archive.reason if self.archive else None


class ProtocolVersionArchive(Base):
    """Revocable-use marker kept separate from an immutable published snapshot."""

    __tablename__ = "PROTOCOL_VERSION_ARCHIVE"

    protocol_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROTOCOL_VERSION.protocol_version_id", ondelete="CASCADE"),
        primary_key=True,
    )
    archived_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    protocol_version: Mapped["ProtocolVersion"] = relationship(
        "ProtocolVersion", back_populates="archive"
    )
    archiver: Mapped["User | None"] = relationship("User")


class ValidatorRelease(Base):
    """Identity and checksum of deterministic validator code/schema."""

    __tablename__ = "VALIDATOR_RELEASE"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_validator_release_name_version"),
        CheckConstraint("length(checksum_sha256) = 64", name="ck_validator_checksum"),
    )

    validator_release_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ValidationRun(Base):
    """Immutable result for a revision, protocol version, and validator release."""

    __tablename__ = "VALIDATION_RUN"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "protocol_version_id",
            "validator_release_id",
            name="uq_validation_run_inputs",
        ),
        CheckConstraint(
            "outcome IN ('passed', 'failed')", name="ck_validation_run_outcome"
        ),
    )

    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("EAF_REVISION.revision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    protocol_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROTOCOL_VERSION.protocol_version_id", ondelete="RESTRICT"),
        nullable=False,
    )
    validator_release_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("VALIDATOR_RELEASE.validator_release_id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome: Mapped[ValidationOutcome] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    revision: Mapped["EafRevision"] = relationship("EafRevision")
    issues: Mapped[list["ProtocolValidationIssue"]] = relationship(
        "ProtocolValidationIssue",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        order_by="ProtocolValidationIssue.issue_number",
    )


class ProtocolValidationIssue(Base):
    """One stable, queryable issue emitted by a validation run."""

    __tablename__ = "VALIDATION_ISSUE"
    __table_args__ = (
        UniqueConstraint(
            "validation_run_id", "issue_number", name="uq_validation_issue_number"
        ),
        CheckConstraint("issue_number > 0", name="ck_validation_issue_positive"),
        CheckConstraint(
            "severity IN ('error', 'warning')", name="ck_validation_issue_severity"
        ),
    )

    validation_issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("VALIDATION_RUN.validation_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[ValidationSeverity] = mapped_column(String(20), nullable=False)
    location: Mapped[str] = mapped_column(String(1000), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    rule_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun", back_populates="issues"
    )


class ProjectComplianceScan(Base):
    """Durable project-wide compliance snapshot against one protocol version."""

    __tablename__ = "PROJECT_COMPLIANCE_SCAN"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_compliance_scan_status",
        ),
        CheckConstraint(
            "trigger IN ('manual', 'preview', 'protocol_pinned')",
            name="ck_compliance_scan_trigger",
        ),
        CheckConstraint(
            "total_files >= 0 AND passed_files >= 0 AND failed_files >= 0",
            name="ck_compliance_scan_counts_nonnegative",
        ),
        CheckConstraint(
            "passed_files + failed_files <= total_files",
            name="ck_compliance_scan_counts_within_total",
        ),
        CheckConstraint(
            "status <> 'running' OR completed_at IS NULL",
            name="ck_compliance_scan_running_incomplete",
        ),
        CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name="ck_compliance_scan_completed_at",
        ),
        Index("ix_compliance_scan_project_started", "project_id", "started_at"),
    )

    scan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    protocol_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROTOCOL_VERSION.protocol_version_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    trigger: Mapped[str] = mapped_column(String(24), nullable=False)
    initiated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project")
    protocol_version: Mapped["ProtocolVersion"] = relationship("ProtocolVersion")
    initiator: Mapped["User | None"] = relationship("User")
    files: Mapped[list["ProjectComplianceScanFile"]] = relationship(
        "ProjectComplianceScanFile",
        back_populates="scan",
        cascade="all, delete-orphan",
    )


class ProjectComplianceScanFile(Base):
    """The immutable validation evidence selected for one file in a scan."""

    __tablename__ = "PROJECT_COMPLIANCE_SCAN_FILE"
    __table_args__ = (
        UniqueConstraint("scan_id", "elan_id", name="uq_compliance_scan_file"),
        CheckConstraint(
            "outcome IN ('passed', 'failed')", name="ck_compliance_file_outcome"
        ),
        Index("ix_compliance_scan_file_scan_outcome", "scan_id", "outcome"),
    )

    scan_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROJECT_COMPLIANCE_SCAN.scan_id", ondelete="CASCADE"),
        nullable=False,
    )
    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ELAN_FILE.elan_id", ondelete="CASCADE"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("EAF_REVISION.revision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("VALIDATION_RUN.validation_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    scan: Mapped["ProjectComplianceScan"] = relationship(
        "ProjectComplianceScan", back_populates="files"
    )
    elan_file: Mapped["ElanFile"] = relationship("ElanFile")
    revision: Mapped["EafRevision"] = relationship("EafRevision")
    validation_run: Mapped["ValidationRun"] = relationship("ValidationRun")
