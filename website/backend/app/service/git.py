import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_MAX_FILE_SIZE_MB, ELAN_PROJECTS_BASE_PATH
from app.core.effective_naming_standard_locations import get_location_id_by_name
from app.core.exceptions import RenameConflictError
from app.crud import elan_file_media as elan_media_crud
from app.crud.effective_naming_standard import get_effective_standards_for_project
from app.crud.elan_file import (
    get_elan_file_by_filename_and_project,
    get_elan_file_name_by_id,
    get_elan_files_by_project,
    update_elan_file_name,
)
from app.crud.pending_upload import (
    get_pending_uploads,
    mark_upload_processed,
    save_pending_upload,
)
from app.crud.project import (
    create_project_db,
    delete_project_db,
    get_project_by_id,
    get_project_by_name,
    get_project_id_by_name,
    list_projects_by_instance,
    list_projects_by_user,
    project_exists_by_name,
    restore_project_db,
)
from app.crud.project_naming_standard import get_standard_with_components_full
from app.elan import compare_eaf, parse_eaf
from app.elan.persistence import document_to_persistence
from app.elan.validation import EafValidationError, validate_eaf
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import ProjectPermission, ReviewCaseState, Status, UserRole
from app.model.notification import Notification
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.model.project_revision import ProjectRevision
from app.model.research_topic import (
    ProjectBaselineTier,
    ResearchTopic,
    ResearchTopicTier,
)
from app.model.review import ReviewCase
from app.model.user import User
from app.schema.common.git import FileStatus
from app.schema.responses.git import (
    BulkRenameResponse,
    FileRenameResponse,
    ProjectInfo,
    ProjectSyncCheckResponse,
    RenameResult,
)
from app.service.database_rename_handler import DatabaseRenameHandler
from app.service.eaf_review import (
    EafReviewUnavailableError,
    compare_repository_eaf,
    validate_repository_eafs,
)
from app.service.elan import ElanService
from app.service.git_operations import (
    FileUploadProcessor,
    GitBranchManager,
    GitCommandRunner,
    GitDiffAnalyzer,
    delete_project_folder,
)
from app.service.git_status_parser import GitFileStatusAnalyzer, GitStatusParser
from app.service.project_revision import (
    append_project_revision,
    verify_project_revision_manifest,
)
from app.service.protocol import (
    get_pinned_protocol_version,
    validate_content_against_protocol,
)
from app.service.research_topics import require_distinct_topic_name
from app.storage.paths import safe_project_path
from app.utils.project_backup import (
    remove_project_backup,
    rename_project_backup_folder,
    restore_project_backup,
    update_backup,
)
from app.utils.project_setup_utils import (
    copy_githooks,
    create_gitignore,
    create_project_structure,
    create_readme,
    update_project_githooks,
)
from app.utils.validation import ValidationUtils

logger = get_logger()
EXPECTED_LOG_FIELDS = 4
MIN_DECLINE_REASON_LENGTH = 3
MIN_RECOVERY_REASON_LENGTH = 10
MIN_NAME_STATUS_FIELDS = 2


@dataclass(frozen=True, slots=True)
class SubmissionContext:
    """Authenticated provenance and validation evidence for one upload batch."""

    username: str
    user_id: int
    base_commit: str
    protocol_validation: dict[str, str | None]
    research_context: dict[str, Any]


class DuplicatePendingContributionError(ValueError):
    """Raised when an identical project snapshot is already awaiting review."""

    def __init__(self, upload_id: int) -> None:
        self.upload_id = upload_id
        super().__init__(
            f"This exact contribution is already awaiting review as contribution #{upload_id}."
        )


class ContributionAlreadyCurrentError(ValueError):
    """Raised when submitted files do not change the accepted project state."""


class GitService:
    """Service for managing Git operations for ELAN projects."""

    def __init__(self, base_path: str | None = None) -> None:
        """Initialize the Git service.

        Args:
            base_path: Custom base path for projects. If None, uses config value.

        """
        if base_path is None:
            current_file = Path(__file__)
            elanora_root = current_file.parent.parent.parent.parent.parent
            self.base_path = elanora_root / ELAN_PROJECTS_BASE_PATH
        else:
            self.base_path = Path(base_path)

        self.base_path.mkdir(parents=True, exist_ok=True)

    def check_git_availability(self) -> dict[str, Any]:
        """Check if Git is available on the system."""
        try:
            runner = GitCommandRunner(self.base_path)
            result = runner.run(["--version"])
            return {
                "git_available": result.returncode == 0,
                "version": result.stdout.strip() if result.returncode == 0 else None,
                "status": "ready" if result.returncode == 0 else "error",
            }
        except FileNotFoundError:
            return {
                "git_available": False,
                "version": None,
                "status": "missing",
                "error": "Git not installed",
            }

    @staticmethod
    def _canonical_commits(runner: GitCommandRunner) -> list[str]:
        """Return only commits from the canonical branch's first-parent history."""
        result = runner.run(
            ["rev-list", "--first-parent", runner.canonical_branch()], check=True
        )
        return [line for line in result.stdout.splitlines() if line]

    @staticmethod
    def _resolve_history_commit(
        runner: GitCommandRunner, target_commit: str
    ) -> tuple[str, list[str]]:
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", target_commit):
            raise ValueError("Invalid project version")
        resolved = runner.run(
            ["rev-parse", "--verify", f"{target_commit}^{{commit}}"], check=False
        )
        if resolved.returncode != 0:
            raise ValueError("Project version not found")
        commit = resolved.stdout.strip()
        canonical = GitService._canonical_commits(runner)
        if commit not in canonical:
            raise ValueError("The selected version is not in accepted project history")
        return commit, canonical

    async def get_accepted_project_history(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """List immutable states from the canonical branch with audit provenance."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        current = runner.get_commit_hash()
        log = runner.run(
            [
                "log",
                "--first-parent",
                "--date=iso-strict",
                "--pretty=format:%H%x1f%aI%x1f%an%x1f%s%x1e",
                runner.canonical_branch(),
            ],
            check=True,
        ).stdout
        events = (
            (
                await db.execute(
                    select(AuditEvent).where(
                        AuditEvent.project_id == project.project_id,
                        AuditEvent.action.in_(
                            ["contribution.accepted", "project.version.restored"]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        actor_ids = {
            event.actor_user_id for event in events if event.actor_user_id is not None
        }
        actors: dict[int, str] = {}
        if actor_ids:
            actor_rows = await db.execute(
                select(User.user_id, User.username).where(User.user_id.in_(actor_ids))
            )
            actors = dict(actor_rows.all())
        provenance: dict[str, AuditEvent] = {}
        for audit_event in events:
            commit = audit_event.details.get(
                "accepted_commit"
            ) or audit_event.details.get("restored_commit")
            if isinstance(commit, str):
                provenance[commit] = audit_event
        versions: list[dict[str, Any]] = []
        for record in log.split("\x1e"):
            fields = record.strip().split("\x1f")
            if len(fields) != EXPECTED_LOG_FIELDS:
                continue
            commit, committed_at, author, message = fields
            current_event = provenance.get(commit)
            details = current_event.details if current_event else {}
            contribution_id = None
            if (
                current_event
                and current_event.action == "contribution.accepted"
                and current_event.resource_id
            ):
                try:
                    contribution_id = int(current_event.resource_id)
                except ValueError:
                    contribution_id = None
            versions.append(
                {
                    "commit": commit,
                    "short_commit": commit[:8],
                    "committed_at": committed_at,
                    "message": (
                        f"Accepted contribution #{contribution_id}"
                        if contribution_id is not None
                        else (
                            f"Restored project to version {str(details.get('target_commit', ''))[:8]}"
                            if current_event
                            and current_event.action == "project.version.restored"
                            else message
                        )
                    ),
                    "author": (
                        actors.get(current_event.actor_user_id, author)
                        if current_event and current_event.actor_user_id is not None
                        else author
                    ),
                    "action": current_event.action
                    if current_event
                    else "project.commit",
                    "contribution_id": contribution_id,
                    "restored_from": details.get("target_commit"),
                    "reason": details.get("reason"),
                    "is_current": commit == current,
                }
            )
        return {
            "project_name": project_name,
            "current_commit": current,
            "versions": versions,
        }

    async def preview_project_version_restore(
        self, project_name: str, target_commit: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Preview files, EAF meaning, and open work affected by a restoration."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        runner = GitCommandRunner(safe_project_path(self.base_path, project_name))
        target, _ = self._resolve_history_commit(runner, target_commit)
        current = runner.get_commit_hash()
        if target == current:
            raise ValueError("The selected version is already current")
        diff = runner.run(
            ["diff", "--name-status", "--find-renames", current, target], check=True
        ).stdout
        files: list[dict[str, str]] = []
        summary = {
            "files": 0,
            "annotations": 0,
            "added": 0,
            "removed": 0,
            "value_changed": 0,
            "timing_changed": 0,
            "tier_changed": 0,
            "reference_changed": 0,
            "media_changed": 0,
        }
        for line in diff.splitlines():
            parts = line.split("\t")
            if len(parts) < MIN_NAME_STATUS_FIELDS:
                continue
            status, filename = parts[0], parts[-1]
            files.append({"status": status, "filename": filename})
            if not filename.lower().endswith(".eaf"):
                continue
            documents = []
            for revision in (current, target):
                blob = runner.run(["show", f"{revision}:{filename}"], check=False)
                documents.append(
                    parse_eaf(blob.stdout.encode()) if blob.returncode == 0 else None
                )
            comparison = compare_eaf(documents[0], documents[1])
            summary["files"] += 1
            summary["annotations"] += len(comparison.changes)
            for change in comparison.changes:
                for kind in change.kinds:
                    summary[kind.value] += 1
            if comparison.before_media_urls != comparison.after_media_urls:
                summary["media_changed"] += 1
        pending = await get_pending_uploads(db, project.project_id)
        affected_ids = [item.upload_id for item in pending]
        review_rows = (
            (
                await db.execute(
                    select(ReviewCase.case_id).where(
                        ReviewCase.project_id == project.project_id,
                        ReviewCase.state.in_(
                            [
                                ReviewCaseState.OPEN.value,
                                ReviewCaseState.CHANGES_REQUESTED.value,
                                ReviewCaseState.RESUBMITTED.value,
                            ]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        return {
            "project_name": project_name,
            "current_commit": current,
            "target_commit": target,
            "files": files,
            "semantic_summary": summary,
            "affected_pending_contributions": len(affected_ids),
            "affected_pending_upload_ids": affected_ids,
            "active_review_cases": len(review_rows),
            "active_review_case_ids": [str(case_id) for case_id in review_rows],
        }

    async def restore_project_version(
        self,
        project_name: str,
        target_commit: str,
        expected_head: str,
        reason: str,
        confirmation: str,
        db: AsyncSession,
        user_id: int,
        actor_name: str | None = None,
    ) -> dict[str, Any]:
        """Restore an accepted tree as a new commit without rewriting history."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        if confirmation != f"RESTORE {project_name}":
            raise ValueError(f'Type "RESTORE {project_name}" to confirm')
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        branch = runner.canonical_branch()
        runner.checkout(branch)
        previous = runner.get_commit_hash()
        if previous != expected_head:
            raise ValueError(
                "Accepted project history changed. Refresh the preview before restoring"
            )
        target, _ = self._resolve_history_commit(runner, target_commit)
        if target == previous:
            raise ValueError("The selected version is already current")
        if runner.run(["status", "--porcelain"], check=True).stdout.strip():
            raise ValueError("The project working tree is not clean")
        eaf_paths = runner.run(
            ["ls-tree", "-r", "--name-only", target, "--", "elan_files"], check=True
        ).stdout.splitlines()
        for filename in eaf_paths:
            if filename.lower().endswith(".eaf"):
                content = runner.run_bytes(
                    ["show", f"{target}:{filename}"], check=True
                ).stdout
                validate_eaf(content)
        runner.run(["read-tree", "--reset", "-u", f"{target}^{{tree}}"], check=True)
        commit_args = [
            "commit",
            "-m",
            f"Restore accepted project version {target[:8]}",
            "-m",
            f"Reason: {reason.strip()}",
        ]
        if actor_name:
            safe_email_name = re.sub(r"[^a-z0-9._-]+", "-", actor_name.lower())
            commit_args = [
                "-c",
                f"user.name={actor_name}",
                "-c",
                f"user.email={safe_email_name}@elanora.local",
                *commit_args,
            ]
        runner.run(commit_args, check=True)
        restored = runner.get_commit_hash()
        try:
            await self.rebuild_project_database(
                project_name, db, user_id, commit_changes=False
            )
            db.add(
                AuditEvent(
                    actor_user_id=user_id,
                    project_id=project.project_id,
                    action="project.version.restored",
                    resource_type="project",
                    resource_id=str(project.project_id),
                    details={
                        "previous_commit": previous,
                        "target_commit": target,
                        "restored_commit": restored,
                        "reason": reason.strip(),
                    },
                )
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=restored,
                parent_git_commit=previous,
                source_type="restoration",
                actor_user_id=user_id,
                details={
                    "target_commit": target,
                    "reason": reason.strip(),
                },
            )
            pending = await get_pending_uploads(db, project.project_id)
            notified_users = {
                upload.submitted_by
                for upload in pending
                if upload.submitted_by not in {None, user_id}
            }
            for submitted_by in notified_users:
                db.add(
                    Notification(
                        user_id=submitted_by,
                        title="Accepted project version changed",
                        message=(
                            f"An administrator restored an earlier state of {project_name}. "
                            "Your open contribution was preserved and its compatibility was re-evaluated."
                        ),
                        action_url=f"/contribution?project={project.project_id}&view=queue",
                    )
                )
            await db.commit()
        except Exception:
            await db.rollback()
            runner.reset_hard(previous)
            raise
        update_backup(project_path.name, project_path.parent)
        return {
            "project_name": project_name,
            "previous_commit": previous,
            "target_commit": target,
            "restored_commit": restored,
            "status": "restored_as_new_version",
        }

    async def create_project(
        self,
        project_name: str,
        description: str | None,
        db: AsyncSession,
        user_id: int,
        instance_id: int,
    ) -> dict[str, Any]:
        """Create a new project with Git repository and description."""
        project_path = safe_project_path(self.base_path, project_name)
        staging_path: Path | None = None
        published = False

        logger.info(f"Checking if project folder exists: {project_path}")
        logger.info(f"Folder exists? {project_path.exists()}")

        if project_path.exists():
            logger.warning(f"Project folder '{project_path}' already exists.")
            raise ValueError(f"Project '{project_name}' already exists")

        exists = await project_exists_by_name(db, project_name)
        logger.info(f"Checking if project exists in DB: {project_name} -> {exists}")
        if exists:
            logger.warning(f"Project '{project_name}' already exists in the database.")
            raise ValueError(f"Project '{project_name}' already exists")

        try:
            # Assemble the complete repository out of sight, on the same
            # filesystem as its final location so publication is atomic.
            staging_path = Path(
                tempfile.mkdtemp(prefix=f".{project_name}.staging-", dir=self.base_path)
            )
            create_project_structure(staging_path)
            runner = GitCommandRunner(staging_path, maintain_backup=False)
            runner.init_repo()

            # Create .gitignore and README
            create_gitignore(staging_path)
            create_readme(staging_path, project_name)

            # Copy githooks
            copy_githooks(staging_path, project_name)

            # Initial commit
            runner.add_all()
            runner.commit("Initial project setup")

            # Paths
            hooks_dir = staging_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            # Save to database
            await create_project_db(
                db=db,
                project_name=project_name,
                description=description,
                project_path=str(project_path),
                instance_id=instance_id,
                creator_user_id=user_id,
            )
            # Flush has succeeded in create_project_db, but PostgreSQL remains
            # uncommitted while the ready repository is atomically published.
            staging_path.rename(project_path)
            published = True
            await db.commit()

            # The recovery cache is derived state. Build it only after both
            # authoritative stores have accepted the project.
            try:
                update_backup(project_name, self.base_path)
            except Exception:
                logger.exception(
                    "Project %r was created, but its recovery cache could not be updated",
                    project_name,
                )

            return {
                "project_name": project_name,
                "path": str(project_path),
                "status": "created",
                "git_initialized": True,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.exception("Project creation failed for %r", project_name)
            # The path and recovery cache were created by this request. Remove
            # both on failure so filesystem and database state cannot diverge.
            try:
                if published:
                    delete_project_folder(project_path)
                elif staging_path is not None:
                    delete_project_folder(staging_path)
                remove_project_backup(project_name)
            except Exception:
                logger.exception(
                    "Unable to clean up failed project creation for %r", project_name
                )
            raise RuntimeError(f"Project creation failed: {e}") from e

    def commit_changes(
        self, project_name: str, commit_message: str, user_name: str = "user"
    ) -> dict[str, Any]:
        """Commit changes to a project."""
        project_path = safe_project_path(self.base_path, project_name)

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")

        try:
            runner = GitCommandRunner(project_path)

            # Check if there are changes to commit
            if not runner.get_status().strip():
                raise ValueError("No changes to commit")

            # Add all changes
            runner.add_all()

            # Commit with user info
            full_message = f"{commit_message}\n\nCommitted by: {user_name}"
            runner.commit(full_message)

            # Get commit hash
            commit_hash = runner.get_commit_hash()

            return {
                "project_name": project_name,
                "message": commit_message,
                "commit_hash": commit_hash,
                "status": "committed",
                "committed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            raise RuntimeError(f"Commit failed: {e}") from e

    async def add_elan_files(  # noqa: PLR0912
        self,
        project_id: int,
        files: list[UploadFile],
        db: AsyncSession,
        user_id: int,
        user_name: str,
        protocol_validation: dict[str, str | None],
        research_context: dict[str, Any] | None = None,
        allow_current_tree: bool = False,
    ) -> dict[str, Any]:
        """Add multiple ELAN files to the project with branch-based workflow."""
        # Fetch project details by ID
        project = await get_project_by_id(db, project_id)
        if not project:
            logger.error(f"Project with ID '{project_id}' not found in database")
            raise ValueError(f"Project with ID '{project_id}' not found")
        logger.info(
            f"Fetched project: project_id={project.project_id}, project_name={project.project_name}"
        )

        project_path = safe_project_path(self.base_path, project.project_name)
        logger.info(
            f"Starting add_elan_files for project ID: {project_id}, user: {user_name}, files: {[f.filename for f in files]}"
        )

        # Get location ID for upload page
        location_id = get_location_id_by_name("uploadPage")
        if location_id is None:
            logger.warning(
                "Location ID for 'uploadPage' not found; defaulting to no compliance check"
            )
        else:
            logger.debug(f"Using location ID: {location_id} for upload page")

        standard = None
        if location_id is not None:
            # Fetch effective standards using CRUD
            effective_standards = await get_effective_standards_for_project(
                db, project_id, location_id
            )
            logger.info(
                f"Fetched {len(effective_standards)} effective standards for project_id={project_id}, location_id={location_id}"
            )
            if effective_standards:
                # Use the first effective standard (adjust if multiple need handling)
                effective_standard = effective_standards[0]
                logger.debug(
                    f"Using effective standard: id={effective_standard.id}, naming_standard_id={effective_standard.naming_standard_id}"
                )
                # Fetch the full naming standard with components
                full_standard = await get_standard_with_components_full(
                    db, effective_standard.naming_standard_id
                )
                if full_standard:
                    # Extract the dict format expected by ValidationUtils
                    standard = {
                        "pattern": full_standard["pattern"],
                        "components": full_standard["components"],
                    }
                    logger.info(
                        f"Fetched full naming standard: pattern='{full_standard['pattern']}', components_count={len(full_standard['components'])}"
                    )
                else:
                    logger.warning(
                        f"No full naming standard found for naming_standard_id={effective_standard.naming_standard_id}"
                    )
            else:
                logger.info(
                    "No effective standards found; proceeding without compliance check"
                )
        else:
            logger.info("No location ID; skipping standard fetching")

        # Check filename compliance for each file
        compliant_files = []
        non_compliant_files = []
        try:
            for file in files:
                filename = file.filename
                if ValidationUtils.is_filename_compliant(standard, filename):
                    compliant_files.append(filename)
                    logger.debug(f"File '{filename}' is compliant with naming standard")
                else:
                    non_compliant_files.append(filename)
                    logger.warning(
                        f"File '{filename}' is non-compliant with naming standard"
                    )
            if non_compliant_files:
                logger.error(
                    f"Compliance check failed for files: {non_compliant_files}"
                )
                raise ValueError(
                    f"Filename '{non_compliant_files[0]}' does not comply with the project's naming standard."
                )  # Raise for first failure
            else:
                logger.info(f"All {len(files)} files are compliant: {compliant_files}")
        except Exception as e:
            logger.error(
                f"Compliance check error for files {[f.filename for f in files]}: {e}",
                exc_info=True,
            )
            raise ValueError(
                f"Filename compliance check failed due to data issue: {e}"
            ) from e
        # Proceed with the rest of the method
        self._validate_upload_request(project_path, files)
        logger.info("Upload request validated successfully")

        branch_name: str | None = None
        contribution_recorded = False
        try:
            # Setup Git environment
            self._configure_git_user(project_path, user_name)
            existing_files = self._get_existing_files(project_path, files)

            # Initialize managers
            branch_manager = GitBranchManager(project_path)
            file_processor = FileUploadProcessor(project_path)
            diff_analyzer = GitDiffAnalyzer(project_path)

            # Create branch and process files
            branch_manager.switch_to_master()
            base_commit = GitCommandRunner(
                project_path, maintain_backup=False
            ).get_commit_hash()
            branch_name = branch_manager.create_upload_branch(user_name, len(files))
            uploaded_files, failed_files = await file_processor.process_files(
                files, existing_files
            )

            if not uploaded_files:
                raise RuntimeError("No files were successfully uploaded")

            # Commit
            file_processor.commit_files(uploaded_files, user_name)
            upload_info = await self._save_upload_for_admin_approval(
                branch_manager,
                diff_analyzer,
                branch_name,
                db=db,
                context=SubmissionContext(
                    username=user_name,
                    user_id=user_id,
                    base_commit=base_commit,
                    protocol_validation=protocol_validation,
                    research_context=research_context or {},
                ),
                project_path=project_path,
                allow_current_tree=allow_current_tree,
            )
            contribution_recorded = True
            auto_accepted = False
            if (
                project.auto_accept_new_files
                and not upload_info["modified_files"]
                and not upload_info["deleted_files"]
                and not failed_files
            ):
                try:
                    await self.complete_pending_upload(
                        project.project_name,
                        upload_info["branch_name"],
                        "auto",
                        db,
                        user_id,
                    )
                    auto_accepted = True
                    upload_info["status"] = "accepted_automatically"
                    upload_info["message"] = (
                        "The valid new files were accepted automatically by project policy."
                    )
                except Exception:
                    logger.exception(
                        "Automatic acceptance failed; contribution remains pending"
                    )
            upload_info["auto_accepted"] = auto_accepted

            # Build response
            logger.info(
                f"Successfully processed upload for project: {project.project_name}"
            )
            return self._build_upload_response(
                project.project_name,
                uploaded_files,
                failed_files,
                existing_files,
                upload_info,
            )

        except (DuplicatePendingContributionError, ContributionAlreadyCurrentError):
            if branch_name and not contribution_recorded:
                self._discard_failed_submission(project_path, branch_name)
            raise
        except Exception as e:
            if branch_name and not contribution_recorded:
                self._discard_failed_submission(project_path, branch_name)
            logger.error(f"Batch file operation failed: {e}")
            raise RuntimeError(f"Failed to add ELAN files: {e}") from e

    @staticmethod
    def _discard_failed_submission(project_path: Path, branch_name: str) -> None:
        """Return to accepted work and remove branches from a failed submission."""
        runner = GitCommandRunner(project_path, maintain_backup=False)
        try:
            runner.checkout(runner.canonical_branch())
            runner.delete_branch_localy(branch_name)
            runner.delete_branch_localy(f"{branch_name}_pending_approval")
        except Exception:
            logger.exception("Unable to clean up failed contribution %s", branch_name)

    async def _save_upload_for_admin_approval(
        self,
        branch_manager: GitBranchManager,
        diff_analyzer: GitDiffAnalyzer,
        branch_name: str,
        db: AsyncSession,
        context: SubmissionContext,
        project_path: Path,
        allow_current_tree: bool = False,
    ) -> dict[str, Any]:
        """Save upload for admin approval instead of attempting immediate merge."""
        logger.info(f"Saving upload branch '{branch_name}' for admin approval")

        project = await get_project_by_name(db, project_path.name)
        if project is None:
            raise FileNotFoundError("Project disappeared while recording contribution")

        # A Git tree identifies the complete submitted content without being
        # affected by author, timestamp, or commit-message differences. Prevent
        # repeated clicks/retries from creating indistinguishable review work.
        runner = GitCommandRunner(project_path)
        submitted_tree = runner.get_tree_hash(branch_name)
        if not allow_current_tree and submitted_tree == runner.get_tree_hash(
            runner.canonical_branch()
        ):
            raise ContributionAlreadyCurrentError(
                "These files are already the current accepted version; no contribution was created."
            )
        for pending in await get_pending_uploads(db, project.project_id):
            if not pending.branch_name:
                continue
            try:
                if runner.get_tree_hash(pending.branch_name) == submitted_tree:
                    raise DuplicatePendingContributionError(pending.upload_id)
            except DuplicatePendingContributionError:
                raise
            except Exception:
                logger.warning(
                    "Could not inspect pending contribution branch %s",
                    pending.branch_name,
                )

        # Analyze what was uploaded
        branch_manager.switch_to_master()
        analysis = diff_analyzer.analyze_merge_differences(branch_name)
        logger.info(
            f"Upload analysis - New: {len(analysis.new_files)}, Modified: {len(analysis.modified_files)}, Deleted: {len(analysis.deleted_files)}"
        )

        # Always save for admin approval (no immediate merging)
        approval_branch_name = f"{branch_name}_pending_approval"
        try:
            # Rename upload branch to indicate it's pending approval
            runner.run(["branch", "-m", branch_name, approval_branch_name], check=True)
            logger.info(
                f"Branch renamed to '{approval_branch_name}' for admin approval"
            )

            # Store basic upload info in database for admin review
            upload_info = {
                "status": "pending_admin_approval",
                "has_conflicts": False,  # Unknown until admin tests merge
                "has_differences": len(analysis.modified_files) > 0
                or len(analysis.deleted_files) > 0,
                "requires_approval": True,
                "branch_name": approval_branch_name,
                "original_branch": branch_name,
                "new_files": analysis.new_files,
                "modified_files": analysis.modified_files,
                "deleted_files": analysis.deleted_files,
                "analysis": analysis,
                "message": f"Upload saved for admin approval. {len(analysis.new_files)} new files, {len(analysis.modified_files)} modified files.",
                "pending_approval_since": datetime.now().isoformat(),
                "uploaded_by": context.username,
                "base_commit": context.base_commit,
                "protocol_validation": context.protocol_validation,
                "research_context": context.research_context,
            }

            # Save upload info to database for admin dashboard
            await self._save_pending_upload_to_db(
                upload_info,
                project_path,
                db,
                context.username,
                context.user_id,
                context.base_commit,
            )

            return upload_info

        except Exception as e:
            logger.error(f"Failed to save upload for approval: {e}")
            # Cleanup on error
            try:
                runner.run(["branch", "-D", approval_branch_name], check=False)
            except Exception:
                logger.exception(
                    "Failed to clean up approval branch %s", approval_branch_name
                )
            raise RuntimeError(f"Failed to save upload for approval: {e}") from e

    async def _save_pending_upload_to_db(
        self,
        upload_info: dict,
        project_path: Path,
        db: AsyncSession,
        username: str,
        user_id: int,
        base_commit: str,
    ) -> None:
        """Save pending upload info to database for admin review."""
        project = await get_project_by_name(db, project_path.name)
        if project is None:
            raise FileNotFoundError("Project disappeared while recording contribution")
        upload_record = {
            "type": "PENDING_UPLOAD",
            "status": "PENDING_ADMIN_APPROVAL",
            "upload_data": {
                "branch_name": upload_info["branch_name"],
                "original_branch": upload_info["original_branch"],
                "uploaded_by": username,
                "new_files_count": len(upload_info["new_files"]),
                "modified_files_count": len(upload_info["modified_files"]),
                "deleted_files_count": len(upload_info["deleted_files"]),
                "new_files": upload_info["new_files"],
                "modified_files": upload_info["modified_files"],
                "deleted_files": upload_info["deleted_files"],
                "pending_since": upload_info["pending_approval_since"],
                "has_differences": upload_info["has_differences"],
                "has_conflicts": upload_info["has_conflicts"],
                "protocol_validation": upload_info["protocol_validation"],
                "research_context": upload_info["research_context"],
            },
            "resolution_info": {
                "can_auto_resolve": False,
                "requires_admin_approval": True,
                "suggested_action": "admin_test_merge",
                "available_strategies": ["test_merge"],
            },
            "detected_at": upload_info["pending_approval_since"],
        }
        pending_upload = await save_pending_upload(
            db,
            project.project_id,
            upload_info["branch_name"],
            upload_record,
            submitted_by=user_id,
            base_commit=base_commit,
        )
        upload_info["upload_id"] = pending_upload.upload_id

        logger.info(
            f"Saved pending upload info for admin review: {upload_info['branch_name']}"
        )

    async def list_projects(
        self, db: AsyncSession, instance_id: int
    ) -> list[ProjectInfo]:
        """List all projects for a given instance.

        Args:
            db (AsyncSession): The database session.
            instance_id (int): The instance identifier.

        Returns:
            list[ProjectInfo]: A list of project information objects.

        """
        projects = await list_projects_by_instance(db, instance_id)
        return [
            ProjectInfo(
                project_id=p.project_id,
                project_name=p.project_name,
                project_description=p.description,
                auto_accept_new_files=p.auto_accept_new_files,
            )
            for p in projects
        ]

    async def list_user_projects(
        self, db: AsyncSession, user_id: int, instance_id: int
    ) -> list[ProjectInfo]:
        """List projects that a specific user has access to."""
        projects = await list_projects_by_user(db, user_id, instance_id)
        permission_rows = await db.execute(
            select(UserToProject.project_id, UserToProject.permission).where(
                UserToProject.user_id == user_id,
                UserToProject.project_id.in_(
                    [project.project_id for project in projects]
                ),
            )
        )
        permissions = dict(permission_rows.all())
        capability_rows = await db.execute(
            select(
                ProjectCapabilityGrant.project_id,
                ProjectCapabilityGrant.capability,
            ).where(
                ProjectCapabilityGrant.user_id == user_id,
                ProjectCapabilityGrant.project_id.in_(
                    [project.project_id for project in projects]
                ),
            )
        )
        capabilities: dict[int, list[str]] = {}
        for project_id, capability in capability_rows.all():
            capabilities.setdefault(project_id, []).append(str(capability))
        return [
            ProjectInfo(
                project_id=p.project_id,
                project_name=p.project_name,
                project_description=p.description,
                auto_accept_new_files=p.auto_accept_new_files,
                permission=str(permissions.get(p.project_id, ProjectPermission.READ)),
                capabilities=capabilities.get(p.project_id, []),
            )
            for p in projects
        ]

    async def init_project_from_folder_upload(
        self,
        project_name: str,
        description: str,
        files: list[UploadFile],
        db: AsyncSession,
        user_id: int,
        instance_id: int,
    ) -> dict:
        """Initialize a new project from a folder upload, saving .eaf files, creating a git repository, and updating the database.

        Args:
            project_name (str): The name of the new project.
            description (str): Description of the project.
            files (list[UploadFile]): List of uploaded files.
            db (AsyncSession): Database session.
            user_id (int): ID of the user creating the project.

        Returns:
            dict: Information about the initialized project.

        Raises:
            ValueError: If the project already exists.

        """
        logger.info(
            "Starting project initialization from folder upload for project: %s",
            project_name,
        )
        logger.info("User ID: %s, Files count: %d", user_id, len(files))
        logger.debug("Files: %s", [f.filename for f in files])

        project_path = safe_project_path(self.base_path, project_name)
        elan_files_dir = project_path / "elan_files"
        logger.debug("Project path: %s", project_path)
        logger.debug("ELAN files directory: %s", elan_files_dir)

        if project_path.exists():
            logger.error("Project path already exists: %s", project_path)
            raise ValueError(f"Project '{project_name}' already exists")

        logger.info("Creating project directories")
        project_path.mkdir(parents=True, exist_ok=True)
        elan_files_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Directories created successfully")

        # Create README.md and .gitignore
        logger.info("Creating gitignore and README files")
        create_gitignore(project_path)
        create_readme(project_path, project_name)
        logger.debug("Project files created")

        # Save only .eaf files, directly in elan_files directory
        logger.info("Processing uploaded files")
        saved_files = []
        for file in files:
            logger.debug("Processing file: %s", file.filename)
            if not file.filename or not file.filename.lower().endswith(".eaf"):
                logger.debug("Skipping non-.eaf file: %s", file.filename)
                continue

            dest_path = elan_files_dir / Path(file.filename).name
            logger.debug("Saving .eaf file: %s to %s", file.filename, dest_path)

            try:
                file_content = await file.read()
                logger.debug("Read %d bytes from %s", len(file_content), file.filename)

                async with aiofiles.open(dest_path, "wb") as f:
                    await f.write(file_content)

                logger.debug("Successfully saved: %s", dest_path)
                saved_files.append(file.filename)
            except Exception as e:
                logger.error("Failed to save file %s: %s", file.filename, e)
                raise

        logger.info("Saved %d .eaf files: %s", len(saved_files), saved_files)

        # Git operations
        logger.info("Initializing Git repository")
        runner = GitCommandRunner(project_path)
        runner.init_repo()
        logger.debug("Git repository initialized")

        runner.add_all()
        logger.debug("Files added to Git")

        runner.commit("Initial commit from uploaded folder")
        logger.debug("Initial commit created")

        try:
            logger.info("Creating project in database")
            await create_project_db(
                db=db,
                project_name=project_name,
                description=description,
                project_path=str(project_path),
                instance_id=instance_id,
                creator_user_id=user_id,
            )
            await db.commit()
            logger.debug("Project created in database successfully")

            logger.info("Processing ELAN files for database")
            elan_service = ElanService(db)
            elan_files = list(elan_files_dir.rglob("*.eaf"))
            logger.info(
                "Found %d .eaf files to process: %s",
                len(elan_files),
                [f.name for f in elan_files],
            )

            processed_files = []
            skipped_files = []
            failed_files = []

            for elan_file in elan_files:
                logger.debug("Processing ELAN file: %s", elan_file)
                try:
                    result = await elan_service.process_single_file(
                        str(elan_file), user_id, project_name
                    )

                    if result["status"] == "processed":
                        processed_files.append(result["filename"])
                    elif result["status"] == "skipped":
                        skipped_files.append(result["filename"])
                    elif result["status"] == "failed":
                        failed_files.append(result["filename"])

                except Exception as e:
                    logger.error("Failed to process ELAN file %s: %s", elan_file, e)
                    failed_files.append(elan_file.name)
                    raise

            await db.commit()
            logger.info(
                "ELAN processing complete. Processed: %d, Skipped: %d, Failed: %d",
                len(processed_files),
                len(skipped_files),
                len(failed_files),
            )

            if skipped_files:
                logger.info("Skipped files (already in database): %s", skipped_files)
            if failed_files:
                logger.warning("Failed files: %s", failed_files)

        except Exception as e:
            await db.rollback()
            logger.error("Failed to initialize project from folder: %s", e)
            logger.error("Rolling back database changes")
            raise

        result = {
            "project_name": project_name,
            "path": str(project_path),
            "status": "initialized",
            "git_initialized": True,
            "created_at": datetime.now().isoformat(),
        }

        logger.info("Project initialization completed successfully")
        logger.debug("Result: %s", result)

        return result

    async def _sync_elan_files_with_db(
        self, project_path: Path, db: AsyncSession, user_id: int, project_name: str
    ):
        """Parse all .eaf files in the project and update the database."""
        elan_service = ElanService(db)
        elan_files = list((project_path / "elan_files").glob("*.eaf"))
        for elan_file in elan_files:
            await elan_service.process_single_file(
                str(elan_file), user_id, project_name
            )

    async def rebuild_project_database(
        self,
        project_name: str,
        db: AsyncSession,
        user_id: int,
        *,
        commit_changes: bool = True,
    ) -> None:
        """Rebuild the mutable database projection from canonical validated EAFs."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        project_path = safe_project_path(self.base_path, project_name)
        files = sorted((project_path / "elan_files").glob("*.eaf"))
        for file_path in files:
            validate_eaf(file_path.read_bytes())
        existing = await get_elan_files_by_project(db, project.project_id)
        existing_names = {item.filename for item, _username in existing}
        canonical_names = {item.name for item in files}
        elan_service = ElanService(db)
        for file_path in files:
            if file_path.name in existing_names:
                await elan_service.process_single_file_and_update(
                    str(file_path),
                    user_id,
                    project_name,
                    commit_changes=commit_changes,
                )
            else:
                await elan_service.process_single_file(
                    str(file_path),
                    user_id,
                    project_name,
                    commit_changes=commit_changes,
                )
        for filename in existing_names - canonical_names:
            if not await elan_service.delete_elan_files_from_db(
                filename, project_name, commit_changes=commit_changes
            ):
                raise RuntimeError(f"Could not remove stale database file {filename}")
        if commit_changes:
            await db.commit()

    async def rebuild_current_revision_projection(
        self,
        project_name: str,
        revision_id: object,
        db: AsyncSession,
        user_id: int,
        *,
        commit_changes: bool = True,
    ) -> dict[str, Any]:
        """Rebuild the mutable query projection from the verified current manifest."""
        project = await db.scalar(
            select(Project)
            .where(Project.project_name == project_name, Project.deleted_at.is_(None))
            .with_for_update()
        )
        if project is None:
            raise FileNotFoundError("Project not found")
        revision = await db.get(ProjectRevision, revision_id)
        if revision is None or revision.project_id != project.project_id:
            raise ValueError("Project revision not found")
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        if runner.get_commit_hash() != revision.git_commit:
            raise ValueError(
                "Only the current accepted project revision can be rebuilt"
            )
        if runner.run(["status", "--porcelain"], check=True).stdout.strip():
            raise ValueError("The project working tree is not clean")

        manifest = await verify_project_revision_manifest(db, revision.revision_id)
        disk_files = sorted((project_path / "elan_files").glob("*.eaf"))
        if [item.name for item in disk_files] != [item.filename for item in manifest]:
            raise RuntimeError("The working tree does not match the revision manifest")
        for path, entry in zip(disk_files, manifest, strict=True):
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry.sha256:
                raise RuntimeError(
                    f"Working-tree checksum mismatch for {entry.filename}"
                )

        elan_service = ElanService(db)
        try:
            existing = await get_elan_files_by_project(db, project.project_id)
            for elan_file, _username in existing:
                if not await elan_service.delete_elan_files_from_db(
                    elan_file.filename, project_name, commit_changes=False
                ):
                    raise RuntimeError(
                        f"Could not remove existing projection for {elan_file.filename}"
                    )
            for entry in manifest:
                document = parse_eaf(entry.raw_xml)
                file_info = document_to_persistence(
                    document,
                    persistence_path=project_path / "elan_files" / entry.filename,
                    modified_at=revision.created_at.replace(tzinfo=None),
                )
                await elan_service.store_elan_file_data(
                    file_info,
                    user_id,
                    project.project_id,
                    commit_changes=False,
                )
            if commit_changes:
                await db.commit()
            else:
                await db.flush()
        except Exception:
            await db.rollback()
            raise
        return {
            "project_name": project_name,
            "revision_id": str(revision.revision_id),
            "manifest_sha256": revision.manifest_sha256,
            "file_count": len(manifest),
            "status": "rebuilt",
        }

    async def get_current_revision_health(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Compare the accepted ledger with disk and the mutable DB projection."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        git_commit = runner.get_commit_hash()
        revision = await db.scalar(
            select(ProjectRevision).where(
                ProjectRevision.project_id == project.project_id,
                ProjectRevision.git_commit == git_commit,
            )
        )
        if revision is None:
            return {
                "project_name": project_name,
                "git_commit": git_commit,
                "status": "ledger_missing",
                "recoverable": False,
            }

        try:
            manifest = await verify_project_revision_manifest(db, revision.revision_id)
        except RuntimeError as exc:
            return {
                "project_name": project_name,
                "revision_id": str(revision.revision_id),
                "git_commit": git_commit,
                "status": "ledger_invalid",
                "recoverable": False,
                "detail": str(exc),
            }
        expected = {entry.filename: entry.sha256 for entry in manifest}
        disk_paths = {
            path.name: path for path in (project_path / "elan_files").glob("*.eaf")
        }
        disk_hashes = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in disk_paths.items()
        }
        latest = (
            select(
                EafRevision.elan_id,
                func.max(EafRevision.revision_number).label("revision_number"),
            )
            .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
            .where(ElanFile.project_id == project.project_id)
            .group_by(EafRevision.elan_id)
            .subquery()
        )
        database = dict(
            (
                await db.execute(
                    select(ElanFile.filename, EafRevision.sha256)
                    .join(latest, latest.c.elan_id == ElanFile.elan_id)
                    .join(
                        EafRevision,
                        (EafRevision.elan_id == latest.c.elan_id)
                        & (EafRevision.revision_number == latest.c.revision_number),
                    )
                    .where(ElanFile.project_id == project.project_id)
                )
            ).all()
        )
        result: dict[str, Any] = {
            "project_name": project_name,
            "revision_id": str(revision.revision_id),
            "git_commit": git_commit,
            "recoverable": True,
            "missing_files": sorted(expected.keys() - disk_hashes.keys()),
            "unexpected_files": sorted(disk_hashes.keys() - expected.keys()),
            "checksum_mismatches": sorted(
                name
                for name in expected.keys() & disk_hashes.keys()
                if expected[name] != disk_hashes[name]
            ),
            "database_missing_files": sorted(expected.keys() - database.keys()),
            "database_unexpected_files": sorted(database.keys() - expected.keys()),
            "database_checksum_mismatches": sorted(
                name
                for name in expected.keys() & database.keys()
                if expected[name] != database[name]
            ),
        }
        issue_keys = (
            "missing_files",
            "unexpected_files",
            "checksum_mismatches",
            "database_missing_files",
            "database_unexpected_files",
            "database_checksum_mismatches",
        )
        result["status"] = (
            "recovery_required" if any(result[key] for key in issue_keys) else "healthy"
        )
        return result

    async def record_current_revision_health(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Persist a scan and notify administrators only on health transitions."""
        project = await db.scalar(
            select(Project)
            .where(Project.project_name == project_name, Project.deleted_at.is_(None))
            .with_for_update()
        )
        if project is None:
            raise FileNotFoundError("Project not found")
        try:
            health = await self.get_current_revision_health(project_name, db)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            health = {
                "project_name": project_name,
                "revision_id": None,
                "git_commit": "",
                "status": "scan_failed",
                "recoverable": False,
                "detail": str(exc),
            }
        now = datetime.now(UTC)
        record = await db.get(ProjectIntegrityStatus, project.project_id)
        previous_status = record.status if record is not None else None
        is_healthy = health["status"] == "healthy"
        details = {
            key: value
            for key, value in health.items()
            if key not in {"project_name", "revision_id", "git_commit", "status"}
        }
        if record is None:
            record = ProjectIntegrityStatus(
                project_id=project.project_id,
                revision_id=health.get("revision_id"),
                status=health["status"],
                details=details,
                first_detected_at=None if is_healthy else now,
                last_checked_at=now,
                resolved_at=None,
            )
            db.add(record)
        else:
            record.revision_id = health.get("revision_id")
            record.status = health["status"]
            record.details = details
            record.last_checked_at = now
            if is_healthy:
                record.resolved_at = (
                    now if previous_status != "healthy" else record.resolved_at
                )
                record.first_detected_at = None
            elif previous_status == "healthy":
                record.first_detected_at = now
                record.resolved_at = None

        transitioned_to_incident = not is_healthy and previous_status in {
            None,
            "healthy",
        }
        transitioned_to_healthy = is_healthy and previous_status not in {
            None,
            "healthy",
        }
        if transitioned_to_incident or transitioned_to_healthy:
            action = (
                "project.integrity.failed"
                if transitioned_to_incident
                else "project.integrity.restored"
            )
            db.add(
                AuditEvent(
                    actor_user_id=None,
                    project_id=project.project_id,
                    action=action,
                    resource_type="project_integrity",
                    resource_id=str(project.project_id),
                    details={"previous_status": previous_status, **health},
                )
            )
            administrator_ids = set(
                (
                    await db.scalars(
                        select(User.user_id)
                        .outerjoin(
                            UserToProject,
                            and_(
                                UserToProject.user_id == User.user_id,
                                UserToProject.project_id == project.project_id,
                            ),
                        )
                        .where(
                            User.is_active.is_(True),
                            or_(
                                and_(
                                    User.instance_id == project.instance_id,
                                    User.role == UserRole.ADMIN,
                                ),
                                UserToProject.permission.in_(
                                    [ProjectPermission.ADMIN, ProjectPermission.OWNER]
                                ),
                            ),
                        )
                    )
                ).all()
            )
            for administrator_id in administrator_ids:
                db.add(
                    Notification(
                        user_id=administrator_id,
                        title=(
                            "Project integrity issue detected"
                            if transitioned_to_incident
                            else "Project integrity restored"
                        ),
                        message=(
                            f"{project_name} no longer matches its accepted revision."
                            if transitioned_to_incident
                            else f"{project_name} matches its accepted revision again."
                        ),
                        action_url=f"/contribution?project={project.project_id}&view=history",
                    )
                )
        await db.commit()
        return health

    async def scan_all_project_integrity(
        self, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Scan every active project without repairing or rewriting project data."""
        project_names = list(
            (
                await db.scalars(
                    select(Project.project_name)
                    .where(Project.deleted_at.is_(None))
                    .order_by(Project.project_id)
                )
            ).all()
        )
        results = []
        for project_name in project_names:
            results.append(await self.record_current_revision_health(project_name, db))
        return results

    async def recover_current_revision_from_manifest(
        self,
        project_name: str,
        revision_id: object,
        db: AsyncSession,
        user_id: int,
        *,
        reason: str,
        confirmation: str,
    ) -> dict[str, Any]:
        """Recover current EAF files and their query projection from the ledger."""
        project = await db.scalar(
            select(Project)
            .where(Project.project_name == project_name, Project.deleted_at.is_(None))
            .with_for_update()
        )
        if project is None:
            raise FileNotFoundError("Project not found")
        if confirmation != f"RECOVER {project_name}":
            raise ValueError(f'Type "RECOVER {project_name}" to confirm')
        if len(reason.strip()) < MIN_RECOVERY_REASON_LENGTH:
            raise ValueError("A recovery reason of at least 10 characters is required")
        revision = await db.get(ProjectRevision, revision_id)
        if revision is None or revision.project_id != project.project_id:
            raise ValueError("Project revision not found")

        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        if runner.get_commit_hash() != revision.git_commit:
            raise ValueError(
                "Only the current accepted project revision can be recovered"
            )
        manifest = await verify_project_revision_manifest(db, revision.revision_id)
        for entry in manifest:
            if Path(entry.filename).name != entry.filename:
                raise RuntimeError("Revision manifest contains an unsafe EAF filename")
            validate_eaf(entry.raw_xml)

        elan_directory = project_path / "elan_files"
        elan_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".{project_path.name}-elanora-recovery-", dir=project_path.parent
        ) as recovery_directory:
            recovery_root = Path(recovery_directory)
            staged_directory = recovery_root / "staged"
            backup_directory = recovery_root / "backup"
            staged_directory.mkdir()
            backup_directory.mkdir()
            for entry in manifest:
                (staged_directory / entry.filename).write_bytes(entry.raw_xml)

            original_paths = sorted(elan_directory.glob("*.eaf"))
            try:
                for path in original_paths:
                    path.replace(backup_directory / path.name)
                for entry in manifest:
                    (staged_directory / entry.filename).replace(
                        elan_directory / entry.filename
                    )
                if runner.run(["status", "--porcelain"], check=True).stdout.strip():
                    raise RuntimeError(
                        "Recovered EAF files do not match the current Git revision"
                    )
                rebuilt = await self.rebuild_current_revision_projection(
                    project_name,
                    revision.revision_id,
                    db,
                    user_id,
                    commit_changes=False,
                )
                db.add(
                    AuditEvent(
                        actor_user_id=user_id,
                        project_id=project.project_id,
                        action="project.revision.recovered",
                        resource_type="project_revision",
                        resource_id=str(revision.revision_id),
                        details={
                            "git_commit": revision.git_commit,
                            "manifest_sha256": revision.manifest_sha256,
                            "reason": reason.strip(),
                        },
                    )
                )
                await db.commit()
            except Exception:
                await db.rollback()
                for path in elan_directory.glob("*.eaf"):
                    path.unlink()
                for path in backup_directory.glob("*.eaf"):
                    path.replace(elan_directory / path.name)
                raise

        return {**rebuilt, "status": "recovered"}

    def _validate_upload_request(
        self, project_path: Path, files: list[UploadFile]
    ) -> None:
        """Validate the upload request."""
        if not project_path.exists():
            raise FileNotFoundError(
                "Project not found at the specified path: {project_path}"
            )
        if not files:
            raise ValueError("No files provided")
        for file in files:
            if not file.filename:
                raise ValueError("All files must have filenames")

    def _get_existing_files(
        self, project_path: Path, files: list[UploadFile]
    ) -> list[str]:
        """Get list of files that already exist."""
        existing_files = []
        for file in files:
            filename = file.filename if file.filename is not None else ""
            dest_path = project_path / "elan_files" / filename
            if filename and dest_path.exists():
                existing_files.append(filename)
        return existing_files

    async def get_pending_uploads_with_status(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Get pending uploads and compute their merge readiness in real-time."""
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)

        # Get pending uploads from DB
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending_uploads = await get_pending_uploads(db, project.project_id)
        configured_baseline_tiers = set(
            (
                await db.scalars(
                    select(ProjectBaselineTier.tier_name).where(
                        ProjectBaselineTier.project_id == project.project_id
                    )
                )
            ).all()
        )

        tree_groups: dict[str, list[int]] = {}
        for upload in pending_uploads:
            if not upload.branch_name:
                continue
            try:
                tree_hash = runner.get_tree_hash(upload.branch_name)
                tree_groups.setdefault(tree_hash, []).append(upload.upload_id)
            except Exception:
                logger.warning(
                    "Could not determine content identity for contribution %s",
                    upload.upload_id,
                )
        duplicate_of = {
            upload_id: min(upload_ids)
            for upload_ids in tree_groups.values()
            for upload_id in upload_ids
            if upload_id != min(upload_ids)
        }
        collision_candidate_ids = {
            upload.upload_id
            for upload in pending_uploads
            if upload.superseded_by_upload_id is None
            and upload.upload_id not in duplicate_of
        }

        upload_status = []
        semantic_targets_by_upload: dict[
            int, dict[str, dict[str, tuple[Any, ...]]]
        ] = {}
        ready_count = 0
        conflicts_count = 0

        for upload in pending_uploads:
            branch_name = upload.branch_name
            git_details = upload.git_details or {}
            upload_data = git_details.get("upload_data", git_details)
            protocol_validation = upload_data.get("protocol_validation") or {}
            current_protocol_id = (
                str(project.protocol_version_id)
                if project.protocol_version_id is not None
                else None
            )
            recorded_protocol_id = protocol_validation.get("protocol_version_id")
            protocol_outcome = (
                "not_configured"
                if current_protocol_id is None
                else (
                    "passed"
                    if protocol_validation.get("outcome") == "passed"
                    and recorded_protocol_id == current_protocol_id
                    else "recheck_required"
                )
            )
            semantic_summary, semantic_targets, changed_tiers = (
                self._pending_semantic_analysis(
                    project_name, branch_name, upload_data, upload.base_commit
                )
            )
            semantic_targets_by_upload[upload.upload_id] = semantic_targets
            research_context = dict(upload_data.get("research_context") or {})
            declared_tiers = {
                tier
                for tier in research_context.get("declared_tiers", [])
                if isinstance(tier, str)
            }
            baseline_tiers = configured_baseline_tiers | {
                tier
                for tier in research_context.get("baseline_tiers", [])
                if isinstance(tier, str)
            }
            outside_scope = sorted(changed_tiers - declared_tiers - baseline_tiers)
            research_context.update(
                {
                    "changed_tiers": sorted(changed_tiers),
                    "baseline_changed_tiers": sorted(changed_tiers & baseline_tiers),
                    "outside_scope_tiers": outside_scope,
                    "scope_status": (
                        "missing_context"
                        if not research_context.get("summary")
                        else "topic_review_needed"
                        if research_context.get("topic_review_status") == "proposed"
                        else "outside_scope"
                        if declared_tiers and outside_scope
                        else "aligned"
                        if declared_tiers
                        else "declared_general"
                    ),
                }
            )

            if upload.superseded_by_upload_id is not None:
                upload_status.append(
                    {
                        "upload_id": upload.upload_id,
                        "branch_name": branch_name,
                        "upload_type": upload.upload_type.value,
                        "description": upload.upload_description,
                        "status": upload.status.value,
                        "uploaded_at": upload.detected_at.isoformat()
                        if upload.detected_at
                        else None,
                        "uploaded_by": upload_data.get("uploaded_by"),
                        "files": {
                            "new": upload_data.get("new_files", []),
                            "modified": upload_data.get("modified_files", []),
                            "deleted": upload_data.get("deleted_files", []),
                        },
                        "quality_checks": {
                            "eaf": "passed",
                            "naming": "passed",
                            "protocol": protocol_outcome,
                        },
                        "semantic_summary": semantic_summary,
                        "research_context": research_context,
                        "superseded_by_upload_id": upload.superseded_by_upload_id,
                        "merge_status": "superseded",
                    }
                )
                continue

            if upload.upload_id in duplicate_of:
                upload_status.append(
                    {
                        "upload_id": upload.upload_id,
                        "branch_name": branch_name,
                        "original_branch": upload_data.get(
                            "original_branch",
                            branch_name.replace("_pending_approval", ""),
                        ),
                        "upload_type": upload.upload_type.value,
                        "description": upload.upload_description,
                        "status": upload.status.value,
                        "uploaded_at": (
                            upload.detected_at.isoformat()
                            if upload.detected_at
                            else None
                        ),
                        "uploaded_by": upload_data.get("uploaded_by"),
                        "files": {
                            "new": upload_data.get("new_files", []),
                            "modified": upload_data.get("modified_files", []),
                            "deleted": upload_data.get("deleted_files", []),
                        },
                        "file_counts": {
                            "new": upload_data.get("new_files_count", 0),
                            "modified": upload_data.get("modified_files_count", 0),
                            "deleted": upload_data.get("deleted_files_count", 0),
                        },
                        "quality_checks": {
                            "eaf": "passed",
                            "naming": "passed",
                            "protocol": protocol_outcome,
                        },
                        "semantic_summary": semantic_summary,
                        "research_context": research_context,
                        "protocol_version_id": recorded_protocol_id,
                        "duplicate_of_upload_id": duplicate_of[upload.upload_id],
                        "git_details": upload.git_details,
                        "merge_status": "duplicate",
                    }
                )
                continue

            # Test merge in real-time to check status
            try:
                readiness = runner.preview_merge(branch_name)
                status = readiness.status
                conflicts = readiness.conflicted_files
                if readiness.can_merge:
                    ready_count += 1
                else:
                    conflicts_count += 1

                upload_status.append(
                    {
                        "upload_id": upload.upload_id
                        if hasattr(upload, "upload_id")
                        else upload.get("upload_id"),
                        "branch_name": branch_name,
                        "original_branch": upload_data.get(
                            "original_branch",
                            branch_name.replace("_pending_approval", ""),
                        ),
                        "upload_type": upload.upload_type.value
                        if hasattr(upload, "upload_type")
                        else upload.get("upload_type", "pending_upload"),
                        "description": upload.upload_description
                        if hasattr(upload, "upload_description")
                        else upload.get("description", ""),
                        "status": upload.status.value
                        if hasattr(upload, "status")
                        else upload.get("status", "pending_admin_approval"),
                        "uploaded_at": upload.detected_at.isoformat()
                        if hasattr(upload, "detected_at") and upload.detected_at
                        else upload.get("uploaded_at"),
                        "uploaded_by": upload_data.get("uploaded_by"),
                        "files": {
                            "new": upload_data.get("new_files", []),
                            "modified": upload_data.get("modified_files", []),
                            "deleted": upload_data.get("deleted_files", []),
                        },
                        "file_counts": {
                            "new": upload_data.get("new_files_count", 0),
                            "modified": upload_data.get("modified_files_count", 0),
                            "deleted": upload_data.get("deleted_files_count", 0),
                        },
                        "quality_checks": {
                            "eaf": "passed",
                            "naming": "passed",
                            "protocol": protocol_outcome,
                        },
                        "semantic_summary": semantic_summary,
                        "research_context": research_context,
                        "protocol_version_id": protocol_validation.get(
                            "protocol_version_id"
                        ),
                        "git_details": upload.git_details,
                        "merge_status": status,
                        "conflicted_files": conflicts,
                        "conflicted_files_count": len(conflicts),
                        "tested_at": datetime.now().isoformat(),
                    }
                )

            except Exception:
                upload_status.append(
                    {
                        "upload_id": upload.upload_id
                        if hasattr(upload, "upload_id")
                        else upload.get("upload_id"),
                        "branch_name": branch_name,
                        "original_branch": upload_data.get(
                            "original_branch",
                            branch_name.replace("_pending_approval", ""),
                        ),
                        "upload_type": upload.upload_type.value
                        if hasattr(upload, "upload_type")
                        else upload.get("upload_type", "pending_upload"),
                        "description": upload.upload_description
                        if hasattr(upload, "upload_description")
                        else upload.get("description", ""),
                        "status": upload.status.value
                        if hasattr(upload, "status")
                        else upload.get("status", "pending_admin_approval"),
                        "uploaded_at": upload.detected_at.isoformat()
                        if hasattr(upload, "detected_at") and upload.detected_at
                        else upload.get("uploaded_at"),
                        "uploaded_by": None,
                        "merge_status": "error",
                        "error": "Unable to inspect this pending upload",
                        "can_auto_merge": False,
                    }
                )

        for item in upload_status:
            upload_id = int(item["upload_id"])
            if upload_id not in collision_candidate_ids:
                item["annotation_collisions"] = []
                continue
            targets = semantic_targets_by_upload.get(upload_id, {})
            collisions = []
            for other_id, other_targets in semantic_targets_by_upload.items():
                if other_id == upload_id or other_id not in collision_candidate_ids:
                    continue
                shared: dict[str, list[str]] = {}
                for filename in targets.keys() & other_targets.keys():
                    differing_ids = sorted(
                        annotation_id
                        for annotation_id in targets[filename].keys()
                        & other_targets[filename].keys()
                        if targets[filename][annotation_id]
                        != other_targets[filename][annotation_id]
                    )
                    if differing_ids:
                        shared[filename] = differing_ids
                if shared:
                    collisions.append(
                        {"contribution_id": other_id, "annotations": shared}
                    )
            item["annotation_collisions"] = sorted(
                collisions, key=lambda collision: collision["contribution_id"]
            )

        return {
            "project_name": project_name,
            "pending_uploads": upload_status,
            "total_pending": len(upload_status),
            "ready_count": ready_count,
            "conflicts_count": conflicts_count,
        }

    def _pending_semantic_analysis(
        self,
        project_name: str,
        branch_name: str,
        upload_data: dict[str, Any],
        base_commit: str | None,
    ) -> tuple[dict[str, int], dict[str, dict[str, tuple[Any, ...]]], set[str]]:
        """Summarize EAF changes and retain targets for concurrency warnings."""
        filenames = {
            filename
            for key in ("new_files", "modified_files", "deleted_files")
            for filename in upload_data.get(key, [])
            if filename.lower().endswith(".eaf")
        }
        summary = {
            "files": 0,
            "annotations": 0,
            "added": 0,
            "removed": 0,
            "value_changed": 0,
            "timing_changed": 0,
            "tier_changed": 0,
            "reference_changed": 0,
            "media_changed": 0,
        }
        targets: dict[str, dict[str, tuple[Any, ...]]] = {}
        changed_tiers: set[str] = set()
        for filename in sorted(filenames):
            try:
                comparison = compare_repository_eaf(
                    self.base_path,
                    project_name,
                    branch_name,
                    filename,
                    accepted_revision=base_commit,
                )
            except (FileNotFoundError, EafReviewUnavailableError, EafValidationError):
                logger.warning(
                    "Could not summarize semantic changes for %s on %s",
                    filename,
                    branch_name,
                )
                continue
            summary["files"] += 1
            summary["annotations"] += len(comparison.changes)
            targets[filename] = {}
            for change in comparison.changes:
                after = change.after
                if change.before is not None:
                    changed_tiers.add(change.before.tier_id)
                if after is not None:
                    changed_tiers.add(after.tier_id)
                targets[filename][change.annotation_id] = (
                    tuple(change.kinds),
                    after.tier_id if after else None,
                    after.value if after else None,
                    after.start_ms if after else None,
                    after.end_ms if after else None,
                    after.annotation_ref if after else None,
                )
                for kind in change.kinds:
                    summary[kind.value] += 1
            if comparison.before_media_urls != comparison.after_media_urls:
                summary["media_changed"] += 1
        return summary, targets, changed_tiers

    def test_pending_upload(
        self, project_name: str, branch_name: str
    ) -> dict[str, Any]:
        """Test a contribution against master without retaining working-tree changes."""
        project_path = safe_project_path(self.base_path, project_name)
        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")
        runner = GitCommandRunner(project_path)
        readiness = runner.preview_merge(branch_name)
        return {
            "status": readiness.status,
            "conflicted_files": readiness.conflicted_files,
            "conflicts_count": len(readiness.conflicted_files),
            "can_auto_merge": readiness.can_merge,
            "tested_at": datetime.now().isoformat(),
        }

    async def set_contribution_research_topic(
        self,
        project_name: str,
        upload_id: int,
        topic_id: int | None,
        new_topic_name: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Resolve a contribution's topic while retaining its declared evidence."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        upload = await db.get(PendingUpload, upload_id)
        if (
            upload is None
            or upload.project_id != project.project_id
            or upload.status != Status.PENDING_ADMIN_APPROVAL
            or not upload.branch_name
        ):
            raise FileNotFoundError("Pending contribution not found")
        if topic_id is not None and new_topic_name:
            raise ValueError("Choose an existing topic or create a new one, not both")

        details = dict(upload.git_details or {})
        upload_data = dict(details.get("upload_data") or {})
        context = dict(upload_data.get("research_context") or {})
        _summary, _targets, changed_tiers = self._pending_semantic_analysis(
            project_name, upload.branch_name, upload_data, upload.base_commit
        )

        topic = None
        if topic_id is not None:
            topic = await db.scalar(
                select(ResearchTopic).where(
                    ResearchTopic.topic_id == topic_id,
                    ResearchTopic.project_id == project.project_id,
                )
            )
            if topic is None:
                raise ValueError("Research topic not found")
        elif new_topic_name:
            cleaned_name = " ".join(new_topic_name.split())
            project_topics = list(
                (
                    await db.scalars(
                        select(ResearchTopic).where(
                            ResearchTopic.project_id == project.project_id
                        )
                    )
                ).all()
            )
            require_distinct_topic_name(cleaned_name, project_topics)
            if not changed_tiers:
                raise ValueError(
                    "A topic cannot be created because no changed tiers were detected"
                )
            topic = ResearchTopic(
                project_id=project.project_id,
                name=cleaned_name,
                description=f"Created while classifying contribution #{upload.upload_id}.",
                allow_new_tiers=False,
                tiers=[
                    ResearchTopicTier(tier_name=name) for name in sorted(changed_tiers)
                ],
            )
            db.add(topic)
            await db.flush()

        context.update(
            {
                "declared_topic_id": topic.topic_id if topic else None,
                "declared_topic_name": topic.name if topic else None,
                "declared_tiers": (
                    sorted(item.tier_name for item in topic.tiers) if topic else []
                ),
                "proposed_topic_name": None,
                "topic_review_status": "verified",
                "topic_match": "administrator_decision",
            }
        )
        upload_data["research_context"] = context
        details["upload_data"] = upload_data
        upload.git_details = details
        await db.commit()
        return context

    async def complete_pending_upload(
        self,
        project_name: str,
        branch_name: str,
        resolution_strategy: str,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Merge a reviewed contribution, synchronize it, and close its queue record."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending = await get_pending_uploads(db, project.project_id)
        pending_upload = next(
            (upload for upload in pending if upload.branch_name == branch_name), None
        )
        if pending_upload is None:
            raise FileNotFoundError("Pending contribution not found")
        if pending_upload.superseded_by_upload_id is not None:
            raise ValueError(
                f"Contribution #{pending_upload.upload_id} was superseded by "
                f"contribution #{pending_upload.superseded_by_upload_id} and cannot be accepted"
            )

        upload_data = dict((pending_upload.git_details or {}).get("upload_data") or {})
        research_context = dict(upload_data.get("research_context") or {})
        if research_context:
            if not str(research_context.get("summary") or "").strip():
                raise ValueError(
                    "The researcher must describe the work before this contribution can be merged"
                )
            if research_context.get("topic_review_status") == "proposed":
                raise ValueError(
                    "Assign the proposed research topic before merging this contribution"
                )

        blocking_review = await db.scalar(
            select(ReviewCase.case_id).where(
                (
                    (ReviewCase.upload_id == pending_upload.upload_id)
                    | (ReviewCase.resubmitted_upload_id == pending_upload.upload_id)
                ),
                ReviewCase.state.in_(
                    [
                        ReviewCaseState.OPEN.value,
                        ReviewCaseState.CHANGES_REQUESTED.value,
                        ReviewCaseState.RESUBMITTED.value,
                    ]
                ),
            )
        )
        if blocking_review is not None:
            raise ValueError(
                "Resolve the contribution's open review cases before accepting it"
            )

        project_path = safe_project_path(self.base_path, project_name)
        submitted_eafs = validate_repository_eafs(project_path, branch_name)
        current_protocol = await get_pinned_protocol_version(db, project)
        protocol_errors = [
            (filename, finding)
            for filename, content in submitted_eafs.items()
            for finding in (
                validate_content_against_protocol(content, current_protocol)
                if current_protocol is not None
                else ()
            )
        ]
        if protocol_errors:
            filename, finding = protocol_errors[0]
            additional = len(protocol_errors) - 1
            suffix = f" and {additional} more issue(s)" if additional else ""
            raise ValueError(
                f"{filename}: {finding.message}{suffix}. Correct the file in ELAN and submit it again."
            )
        runner = GitCommandRunner(project_path)
        parent_commit = runner.get_commit_hash()
        result = runner.complete_pending_merge(branch_name, resolution_strategy)
        accepted_commit = runner.get_commit_hash()
        try:
            await self.rebuild_project_database(
                project_name, db, user_id, commit_changes=False
            )
            await mark_upload_processed(
                db,
                project.project_id,
                branch_name,
                user_id,
                accepted_commit,
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=accepted_commit,
                parent_git_commit=parent_commit,
                source_type="contribution",
                actor_user_id=user_id,
                contribution_id=pending_upload.upload_id,
                details={
                    "branch_name": branch_name,
                    "base_commit": pending_upload.base_commit or "",
                    "resolution_strategy": resolution_strategy,
                },
            )
            db.add(
                AuditEvent(
                    actor_user_id=user_id,
                    project_id=project.project_id,
                    action="contribution.accepted",
                    resource_type="pending_upload",
                    resource_id=str(pending_upload.upload_id),
                    details={
                        "branch_name": branch_name,
                        "base_commit": pending_upload.base_commit,
                        "accepted_commit": accepted_commit,
                        "resolution_strategy": resolution_strategy,
                        "merge_status": result["status"],
                        "protocol_version_id": (
                            str(current_protocol.protocol_version_id)
                            if current_protocol is not None
                            else None
                        ),
                    },
                )
            )
            if pending_upload.submitted_by not in {None, user_id}:
                db.add(
                    Notification(
                        user_id=pending_upload.submitted_by,
                        title="Contribution accepted",
                        message=f"Your contribution to {project_name} is now part of the project.",
                        action_url=f"/contribution?project={project.project_id}",
                    )
                )
            await db.commit()
        except Exception:
            await db.rollback()
            runner.reset_hard(parent_commit)
            update_backup(project_path.name, project_path.parent)
            raise
        runner.delete_branch_localy(branch_name)
        update_backup(project_path.name, project_path.parent)
        return {
            "project_name": project_name,
            **result,
            "accepted_commit": accepted_commit,
            "resolved_at": datetime.now().isoformat(),
        }

    async def dismiss_duplicate_upload(
        self,
        project_name: str,
        upload_id: int,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Dismiss a verified duplicate while retaining its audit record."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending = await get_pending_uploads(db, project.project_id)
        upload = next((item for item in pending if item.upload_id == upload_id), None)
        if upload is None or not upload.branch_name:
            raise FileNotFoundError("Pending contribution not found")

        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        submitted_tree = runner.get_tree_hash(upload.branch_name)
        original = next(
            (
                item
                for item in sorted(pending, key=lambda item: item.upload_id)
                if item.upload_id < upload.upload_id
                and item.branch_name
                and runner.get_tree_hash(item.branch_name) == submitted_tree
            ),
            None,
        )
        if original is None:
            raise ValueError(
                "This contribution is not a duplicate of an earlier pending contribution"
            )

        upload.status = Status.DISMISSED
        upload.resolved_at = datetime.now()
        upload.resolved_by = user_id
        db.add(
            AuditEvent(
                actor_user_id=user_id,
                project_id=project.project_id,
                action="contribution.duplicate_dismissed",
                resource_type="pending_upload",
                resource_id=str(upload.upload_id),
                details={"duplicate_of_upload_id": original.upload_id},
            )
        )
        if upload.submitted_by not in {None, user_id}:
            db.add(
                Notification(
                    user_id=upload.submitted_by,
                    title="Duplicate contribution dismissed",
                    message=(
                        f"Your contribution to {project_name} matched contribution "
                        f"#{original.upload_id}; no research data was lost."
                    ),
                    action_url=f"/contribution?project={project.project_id}",
                )
            )
        await db.commit()
        try:
            runner.delete_branch_localy(upload.branch_name)
        except Exception:
            logger.exception(
                "Could not remove dismissed duplicate branch %s", upload.branch_name
            )
        return {
            "status": "dismissed",
            "upload_id": upload.upload_id,
            "duplicate_of_upload_id": original.upload_id,
        }

    async def decline_pending_upload(
        self,
        project_name: str,
        upload_id: int,
        reason: str,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Terminally decline pending work without erasing its audit history."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        upload = await db.get(PendingUpload, upload_id)
        if (
            upload is None
            or upload.project_id != project.project_id
            or upload.status != Status.PENDING_ADMIN_APPROVAL
            or not upload.branch_name
        ):
            raise FileNotFoundError("Pending contribution not found")

        decline_reason = reason.strip()
        if len(decline_reason) < MIN_DECLINE_REASON_LENGTH:
            raise ValueError("A decline reason is required")

        upload.status = Status.DISMISSED
        upload.resolved_at = datetime.now()
        upload.resolved_by = user_id
        review_cases = list(
            (
                await db.scalars(
                    select(ReviewCase).where(
                        ReviewCase.project_id == project.project_id,
                        (
                            (ReviewCase.upload_id == upload.upload_id)
                            | (ReviewCase.resubmitted_upload_id == upload.upload_id)
                        ),
                        ReviewCase.state.not_in(
                            [ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED]
                        ),
                    )
                )
            ).all()
        )
        for review_case in review_cases:
            review_case.state = ReviewCaseState.CLOSED
            review_case.resolved_at = datetime.now()
            review_case.updated_at = datetime.now()

        db.add(
            AuditEvent(
                actor_user_id=user_id,
                project_id=project.project_id,
                action="contribution.declined",
                resource_type="pending_upload",
                resource_id=str(upload.upload_id),
                details={
                    "branch_name": upload.branch_name,
                    "reason": decline_reason,
                    "closed_review_case_ids": [
                        str(review_case.case_id) for review_case in review_cases
                    ],
                },
            )
        )
        if upload.submitted_by not in {None, user_id}:
            db.add(
                Notification(
                    user_id=upload.submitted_by,
                    title="Contribution declined",
                    message=f"Your contribution to {project_name} was declined: {decline_reason}",
                    action_url=f"/contribution?project={project.project_id}",
                )
            )
        await db.commit()
        try:
            GitCommandRunner(
                safe_project_path(self.base_path, project_name)
            ).delete_branch_localy(upload.branch_name)
        except Exception:
            logger.exception("Could not remove declined branch %s", upload.branch_name)
        return {"status": "dismissed", "upload_id": upload.upload_id}

    def _build_upload_response(
        self,
        project_name: str,
        uploaded_files,
        failed_files,
        existing_files: list[str],
        upload_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the upload response for the admin approval workflow."""
        return {
            "project_name": project_name,
            "upload_id": upload_info.get("upload_id"),
            "branch_name": upload_info.get("branch_name"),  # Use approval branch name
            "uploaded_files": [self._convert_upload_result(f) for f in uploaded_files],
            "failed_files": [self._convert_upload_result(f) for f in failed_files],
            "total_uploaded": len(uploaded_files),
            "total_failed": len(failed_files),
            "existing_files_updated": len(existing_files),
            "new_files_added": len(uploaded_files) - len(existing_files),
            # Workflow status
            "status": upload_info["status"],  # "pending_admin_approval"
            "requires_approval": upload_info.get("requires_approval", True),
            "has_differences": upload_info.get("has_differences", False),
            "auto_accepted": upload_info.get("auto_accepted", False),
            # Upload summary
            "upload_summary": {
                "new_files": upload_info.get("new_files", []),
                "modified_files": upload_info.get("modified_files", []),
                "deleted_files": upload_info.get("deleted_files", []),
            },
            # Admin workflow info
            "admin_info": {
                "pending_approval_since": upload_info.get("pending_approval_since"),
                "approval_branch": upload_info.get("branch_name"),
                "original_branch": upload_info.get("original_branch"),
                "next_steps": "Upload saved for admin approval. Admin needs to test merge and resolve any conflicts.",
            },
            "uploaded_at": datetime.now().isoformat(),
            "message": upload_info.get(
                "message", "Upload completed and saved for admin approval"
            ),
        }

    def _convert_upload_result(self, result) -> dict:
        """Convert FileUploadResult to dict for response."""
        if hasattr(result, "success"):
            return {
                "filename": result.filename,
                "size": result.size,
                "existed": result.existed,
            }
        return result  # Already a dict

    def get_branches(self, project_name: str) -> dict[str, Any]:
        """Get all branches for a project."""
        project_path = safe_project_path(self.base_path, project_name)

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")

        try:
            runner = GitCommandRunner(project_path)
            branches_raw = runner.get_branches()
            branches = []
            current_branch = None

            for line in branches_raw:
                stripped_line = line.strip()
                if stripped_line.startswith("* "):
                    current_branch = stripped_line[2:]
                    branches.append({"name": current_branch, "is_current": True})
                elif stripped_line and not stripped_line.startswith("remotes/"):
                    branches.append({"name": stripped_line, "is_current": False})

            return {
                "project_name": project_name,
                "branches": branches,
                "current_branch": current_branch,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get branches: {e}") from e

    async def resolve_conflicts(
        self,
        project_name: str,
        branch_name: str,
        resolution_strategy: str,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Resolve conflicts and merge a branch, then sync ELAN files with DB."""
        project_path = safe_project_path(self.base_path, project_name)

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")

        try:
            runner = GitCommandRunner(project_path)
            result = runner.resolve_conflicts(branch_name, resolution_strategy)

            # --- Sync DB with merged ELAN files ---
            await self._sync_elan_files_with_db(project_path, db, user_id, project_name)

            return {
                "project_name": project_name,
                **result,
                "resolved_at": datetime.now().isoformat(),
            }

        except Exception as e:
            raise RuntimeError(f"Failed to resolve conflicts: {e}") from e

    def _configure_git_user(self, project_path: Path, instance_name: str) -> None:
        runner = GitCommandRunner(project_path)
        runner.configure_user(instance_name)

    def _create_readme(self, project_name: str) -> str:
        """Generate README content for a new project."""
        return f"# {project_name}\n\nThis is the ELAN project '{project_name}'.\n"

    def _parse_git_status(self, status_output: str) -> list[dict[str, str]]:
        """Parse the output of 'git status --porcelain'."""
        files = []
        pattern = re.compile(r"^([ MADRCU\?]{1,2})\s+(.*)$")
        for line in status_output.strip().splitlines():
            if not line:
                continue
            match = pattern.match(line)
            if match:
                status = match.group(1).strip()
                filename = match.group(2).strip()
                files.append({"filename": filename, "status": status})
        return files

    def _get_recent_commits(
        self, project_path: Path, count: int = 5
    ) -> list[dict[str, str]]:
        """Get recent commits for the project."""
        runner = GitCommandRunner(project_path)
        result = runner.get_log(count)
        commits = []
        for line in result.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == EXPECTED_LOG_FIELDS:
                commits.append(
                    {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    }
                )
        return commits

    def checkout_branch(self, project_name: str, branch_name: str) -> dict[str, str]:
        """Switch to a different branch in the given project."""
        project_path = safe_project_path(self.base_path, project_name)
        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")
        try:
            runner = GitCommandRunner(project_path)
            runner.checkout(branch_name)
            return {
                "project_name": project_name,
                "branch_name": branch_name,
                "status": "checked_out",
                "message": f"Switched to branch '{branch_name}' in project '{project_name}'.",
            }
        except Exception as e:
            raise RuntimeError(f"Failed to checkout branch: {e}") from e

    async def list_project_files(
        self, project_name: str, db: AsyncSession, include_media: bool = False
    ) -> dict[str, Any]:
        """Return enriched .eaf files for the project using CRUD, optionally with media information."""
        project = await get_project_by_name(db, project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found.")

        # Use CRUD to get files with user info
        db_files = await get_elan_files_by_project(db, project.project_id)

        # If media is requested, get media information
        media_mapping = {}
        if include_media:
            files_with_media = (
                await elan_media_crud.get_project_files_with_media_simple(
                    db, project.project_id
                )
            )

            # Create a mapping of filename to media info
            media_mapping = {
                file_data["filename"]: {
                    "media_filenames": file_data["media_filenames"],
                    "elan_id": file_data["elan_id"],
                }
                for file_data in files_with_media
            }

        enriched_files = []
        for elan_file, username in db_files:
            file_path = Path(elan_file.absolute_file_path)
            logger.info(f"Getting info for file: {file_path}")

            # Build base file info
            file_info = {
                "name": elan_file.filename,
                "size": elan_file.file_size,
                "lastModified": elan_file.last_modified.isoformat()
                if elan_file.last_modified
                else None,
                "lastUpdatedBy": username or "N/A",
                "type": "file",
            }

            # Add media information if requested
            if include_media:
                if elan_file.filename in media_mapping:
                    media_info = media_mapping[elan_file.filename]
                    file_info["media_filenames"] = media_info["media_filenames"]
                    file_info["elan_id"] = media_info["elan_id"]
                else:
                    file_info["media_filenames"] = []
                    file_info["elan_id"] = elan_file.elan_id

            enriched_files.append(file_info)

        logger.info(f"Retrieved files for project '{project_name}': {enriched_files}")
        return {"files": enriched_files}

    async def synchronize_project(
        self,
        project_name: str,
        db: AsyncSession,
        user_id: int,
        operation_id: str | None = None,
    ) -> dict:
        """Idempotently synchronize the project's elan_files with the database."""
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)

        logger.info(f"Starting synchronization for project: {project_name}")

        # Inspect first. Nothing is staged until every changed EAF passes preflight.
        elan_files_dir = project_path / "elan_files"
        status_output = runner.get_status()

        logger.info(f"Git status output: '{status_output}'")

        # Use GitStatusParser for cleaner parsing
        parser = GitStatusParser()
        analyzer = GitFileStatusAnalyzer(parser)

        # Get all Git-tracked files
        all_tracked_result = runner.run(["ls-files"], check=True)
        all_tracked_files = set(all_tracked_result.stdout.strip().splitlines())
        logger.info(f"All tracked files in Git: {all_tracked_files}")

        # Use the analyzer to process all files
        files_status, processed_files = analyzer.analyze_project_files(
            status_output, all_tracked_files, elan_files_dir
        )
        logger.info(f"Processed files: {processed_files}")
        logger.info(f"Files status: {files_status}")

        elan_service = ElanService(db)
        updated_files = []
        deleted_files = []

        logger.info(f"Processing {len(files_status)} file status changes")

        self._validate_sync_candidates(project_path, files_status)

        # Establish the Git snapshot only after the complete batch passes validation.
        runner.add_all()

        for file_status in files_status:
            filename = file_status.filename
            status = file_status.status
            file_path = project_path / filename

            logger.info(f"Processing file: {filename} with status: {status}")

            try:
                if status in {"added", "untracked"}:
                    if file_path.exists():
                        logger.info(f"Adding new file in DB: {file_path}")
                        await elan_service.process_single_file(
                            str(file_path), user_id, project_name
                        )
                        updated_files.append(file_path)
                        logger.info(f"Successfully added file to DB: {file_path}")
                    else:
                        logger.warning(
                            f"File marked as {status} but doesn't exist: {file_path}"
                        )
                elif status == "modified":
                    if file_path.exists():
                        logger.info(f"Updating modified file in DB: {file_path}")
                        await elan_service.process_single_file_and_update(
                            str(file_path), user_id, project_name
                        )
                        updated_files.append(file_path)
                        logger.info(f"Successfully updated file in DB: {file_path}")
                    else:
                        logger.warning(
                            f"File marked as modified but doesn't exist: {file_path}"
                        )
                elif status == "deleted":
                    logger.info(f"Removing deleted file from DB: {filename}")
                    await elan_service.delete_elan_files_from_db(filename, project_name)
                    deleted_files.append(filename)
                    logger.info(f"Successfully deleted file from DB: {filename}")
                elif status == "renamed":
                    # Handle Git-detected renames by updating database filename
                    old_filename = file_status.old_filename
                    new_filename = file_status.new_filename

                    logger.info(f"Processing rename: {old_filename} -> {new_filename}")

                    if old_filename and new_filename:
                        # Extract just the filename from the full path for database lookup
                        old_filename_only = Path(old_filename).name
                        new_filename_only = Path(new_filename).name

                        logger.info(
                            f"Database rename: {old_filename_only} -> {new_filename_only}"
                        )
                        rename_handler = DatabaseRenameHandler(db)
                        success = await rename_handler.process_rename(
                            old_filename_only, new_filename_only, project_name
                        )
                        if success:
                            updated_files.append(project_path / new_filename)
                        else:
                            logger.warning(
                                f"Failed to process rename: {old_filename_only} -> {new_filename_only}"
                            )
                    else:
                        logger.warning(
                            f"Rename detected but missing old/new filename info: {file_status}"
                        )
                else:
                    logger.warning(f"Unknown status '{status}' for file: {filename}")
            except Exception as e:
                logger.error(
                    f"Failed to process file {filename} with status {status}: {e}"
                )
                await db.rollback()
                raise RuntimeError(f"Failed to synchronize {filename}") from e

        # Commit database changes if any were made
        await db.commit()
        logger.info("Database changes committed")

        # Commit changes if any
        status_output = runner.get_status()
        if status_output.strip():
            message = f"Synchronized project '{project_name}' with ELAN files"
            if operation_id:
                message += f"\n\nELANORA-Sync-Operation: {operation_id}"
            runner.commit(message)

        logger.info(f"Synchronization complete for project: {project_name}")

        # Return a status/check response
        return ProjectSyncCheckResponse(
            project_name=project_name,
            in_sync=True,
            files_status=[
                FileStatus(
                    filename=str(f), status="updated", description="File updated"
                )
                for f in updated_files
            ]
            + [
                FileStatus(filename=f, status="deleted", description="File deleted")
                for f in deleted_files
            ],
        ).model_dump()

    def validate_sync_changes(
        self, project_name: str, changes: list[dict[str, object]]
    ) -> None:
        """Apply the canonical EAF preflight to a serialized preview."""
        project_path = safe_project_path(self.base_path, project_name)
        self._validate_sync_candidates(
            project_path, [FileStatus.model_validate(change) for change in changes]
        )

    @staticmethod
    def _validate_sync_candidates(
        project_path: Path, files_status: list[FileStatus]
    ) -> None:
        """Reject a recovery batch before staging if any changed EAF is unsafe."""
        for file_status in files_status:
            if file_status.status == "deleted":
                continue
            candidate = project_path / file_status.filename
            if not candidate.exists() and file_status.new_filename:
                candidate = project_path / file_status.new_filename
            if not candidate.is_file():
                raise ValueError(
                    f"Changed ELAN file is missing: {file_status.filename}"
                )
            if candidate.stat().st_size > ELAN_MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(
                    f"Changed ELAN file exceeds {ELAN_MAX_FILE_SIZE_MB}MB: {candidate.name}"
                )
            validate_eaf(candidate.read_bytes())

    async def delete_project(self, project_name: str, db: AsyncSession):
        """Delete a project by its ID."""
        logger.info(f"Starting deletion of project: {project_name}")
        # Remove all DB artifacts (project, files, annotations, etc.)
        try:
            await delete_project_db(db, project_name)
            logger.info(f"Database records deleted for project: {project_name}")
            await db.commit()
        except Exception as db_exc:
            await db.rollback()
            logger.error(
                f"Failed to delete project from DB: {project_name} | Error: {db_exc}"
            )
            raise

        # Remove the project folder from disk
        if not project_name:
            logger.error(f"Project name not found for project_name: {project_name}")
            raise ValueError(f"Project name not found for project_name: {project_name}")
        project_path = safe_project_path(self.base_path, project_name)
        delete_project_folder(project_path)

    async def edit_project(
        self,
        old_project_name: str,
        new_project_name: str,
        new_project_description: str | None,
        db: AsyncSession,
    ) -> dict:
        """Edit an existing project both in the filesystem and in the database.

        Args:
            old_project_name (str): The current name of the project.
            new_project_name (str): The new name to assign to the project.
            new_project_description (str | None): The new description.
            db (AsyncSession): The database session.

        Returns:
            dict: A dictionary containing the new project name and description.

        Raises:
            ValueError: If the old project is not found in the database.
            FileNotFoundError: If the old project folder does not exist.
            FileExistsError: If the target project folder already exists.
            Exception: If renaming the folder fails.

        """
        logger.info(
            f"Starting edit of project: '{old_project_name}' to '{new_project_name}'"
        )
        project = await get_project_by_name(db, old_project_name)
        if not project:
            logger.error(f"Project '{old_project_name}' not found in DB")
            raise ValueError(f"Project '{old_project_name}' not found in DB")

        old_path = safe_project_path(self.base_path, old_project_name)

        # Only rename if the name is actually changed
        if new_project_name != old_project_name:
            new_path = safe_project_path(self.base_path, new_project_name)
            if not old_path.exists():
                logger.error(
                    f"Project folder '{old_project_name}' not found at {old_path}"
                )
                raise FileNotFoundError(
                    f"Project folder '{old_project_name}' not found"
                )
            if new_path.exists():
                logger.error(
                    f"Target project folder '{new_project_name}' already exists at {new_path}"
                )
                raise FileExistsError(
                    f"Target project folder '{new_project_name}' already exists"
                )
            try:
                os.rename(old_path, new_path)
                logger.info(f"Renamed folder from '{old_path}' to '{new_path}'")
            except Exception as e:
                logger.error(f"Failed to rename folder: {e}")
                raise

            project.project_name = new_project_name
            project.project_path = str(new_path)
            rename_project_backup_folder(old_project_name, project.project_name)
            update_project_githooks(new_path, project.project_name)
        else:
            # Name unchanged, just update description
            logger.info("Project name unchanged, only updating description.")

        project.description = new_project_description
        await db.commit()
        logger.info(
            f"Edited project in DB: '{old_project_name}' -> '{new_project_name}'"
        )
        logger.info(f"Changed project description to: {new_project_description}")
        return {
            "new_project_name": new_project_name,
            "new_project_description": new_project_description,
        }

    def synchronize_project_check(self, project_name: str) -> dict:
        """Check for changes in a Git-managed project and analyze file status.

        Analyzes the Git status to detect file changes in the elan_files directory
        and compares against tracked files to determine sync status.

        Args:
            project_name: Name of the project to check for changes

        Returns:
            Dictionary containing project sync status and file change information

        """
        project_path = safe_project_path(self.base_path, project_name)
        elan_files_dir = project_path / "elan_files"
        git_dir = project_path / ".git"

        logger.info(f"GitService base_path: {self.base_path}")
        logger.info(f"Project path: {project_path}")
        logger.info(f"Project path exists: {project_path.exists()}")

        if not project_path.exists():
            return {
                "project_name": project_name,
                "status": "missing_folder",
                "in_sync": False,
                "files_status": [],
            }
        if not git_dir.exists():
            return {
                "project_name": project_name,
                "status": "missing_git",
                "in_sync": False,
                "files_status": [],
            }
        if not elan_files_dir.exists():
            return {
                "project_name": project_name,
                "status": "missing_elan_files",
                "in_sync": False,
                "files_status": [],
            }

        runner = GitCommandRunner(project_path)

        # Preview must not stage or otherwise alter administrator edits.
        status_output = runner.get_status()

        logger.info(f"Git status output: '{status_output}'")

        # Use GitStatusParser for cleaner parsing
        parser = GitStatusParser()
        analyzer = GitFileStatusAnalyzer(parser)

        # Get all Git-tracked files
        all_tracked_result = runner.run(["ls-files"], check=True)
        all_tracked_files = set(all_tracked_result.stdout.strip().splitlines())
        logger.info(f"All tracked files in Git: {all_tracked_files}")

        # Use the analyzer to process all files
        files_status, processed_files = analyzer.analyze_project_files(
            status_output, all_tracked_files, elan_files_dir
        )

        logger.info(f"Processed files: {processed_files}")
        logger.info(f"Files status: {files_status}")

        in_sync = not bool(files_status)

        return ProjectSyncCheckResponse(
            project_name=project_name, in_sync=in_sync, files_status=files_status
        ).model_dump()

    def discard_local_changes(self, project_name: str) -> str:
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        remotes = runner.run(["remote", "-v"]).stdout.strip()
        if "origin" in remotes:
            logger.info(f"Remote 'origin' found for project '{project_name}'")
            runner.run(["fetch", "origin"], check=True)
            runner.reset_hard("origin/master")
        else:
            logger.warning(f"No remote 'origin' found for project '{project_name}'")
            runner.reset_hard()
        runner.clean(force=True, directories=True)
        return "Local changes discarded and folder reset to match the latest remote master."

    async def restore_project_from_backup(
        self, project_name: str, db: AsyncSession, user_id: int
    ) -> str:
        """Restore the project folder from the most recent backup (including .git, elan_files, README.md).

        and update the database to match the restored state.
        """
        restore_project_backup(project_name, self.base_path)
        try:
            await restore_project_db(db, project_name)
            await self.synchronize_project(project_name, db, user_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return (
            f"Project '{project_name}' restored from backup and database synchronized."
        )

    async def decline_project_backup(self, db: AsyncSession, project_name: str) -> None:
        """Remove the backup folder for the project and delete all related data."""
        # Remove backup
        remove_project_backup(project_name)

        # Determine if the project folder exists
        project_path = safe_project_path(self.base_path, project_name)
        if project_path.exists():
            delete_project_folder(project_path)

        # Remove all DB artifacts
        await delete_project_db(db, project_name)
        await db.commit()

    async def rename_file(
        self, project_name: str, elan_id: int, new_filename: str, db: AsyncSession
    ) -> FileRenameResponse:
        """Rename a single file in the project using elan_id."""
        project_path = safe_project_path(self.base_path, project_name)

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")

        # Get current filename from database
        old_filename = await get_elan_file_name_by_id(db, elan_id)
        if not old_filename:
            raise FileNotFoundError(f"ELAN file with ID {elan_id} not found")

        old_file_path = project_path / "elan_files" / old_filename
        new_file_path = project_path / "elan_files" / new_filename

        if not old_file_path.exists():
            raise FileNotFoundError(
                f"File '{old_filename}' not found in project filesystem"
            )

        # Check for conflict: if target filename already exists, get its elan_id
        if new_file_path.exists():
            conflict_elan_id = None
            # Get project_id to find the conflicting file
            project_id = await get_project_id_by_name(db, project_name)
            if project_id:
                conflicting_file = await get_elan_file_by_filename_and_project(
                    db, new_filename, project_id
                )
                if conflicting_file:
                    conflict_elan_id = conflicting_file.elan_id

            # Raise custom conflict exception with conflict info
            logger.warning(
                f"Rename conflict detected: {new_filename} already exists (conflict_elan_id={conflict_elan_id})"
            )
            raise RenameConflictError(
                f"File '{new_filename}' already exists in project",
                conflict_elan_id=conflict_elan_id,
                message_key="rename_file_conflict",
            )

        try:
            # 1. Update database first
            await update_elan_file_name(db, elan_id, new_filename)
            logger.info(
                f"Updated database filename for elan_id={elan_id}: {old_filename} -> {new_filename}"
            )

            # 2. Rename the file on filesystem
            old_file_path.rename(new_file_path)
            logger.info(f"Renamed file on filesystem: {old_filename} -> {new_filename}")

            # 3. Update git (add the rename operation)
            runner = GitCommandRunner(project_path)
            runner.add_all()  # Add all changes including the rename
            commit_hash = runner.commit(
                f"Rename file: {old_filename} -> {new_filename}"
            )
            logger.info(f"Committed rename to git with hash: {commit_hash}")

            # 4. Commit database transaction
            await db.commit()
            logger.info(
                f"Successfully completed file rename: {old_filename} -> {new_filename}"
            )

            return FileRenameResponse(
                project_name=project_name,
                old_filename=old_filename,
                new_filename=new_filename,
                success=True,
                committed=True,
                commit_hash=commit_hash,
                renamed_at=datetime.now().isoformat(),
                message=f"Successfully renamed {old_filename} to {new_filename}",
            )

        except Exception as e:
            logger.error(f"Error during file rename: {e!s}")

            # Rollback database
            await db.rollback()
            logger.info("Rolled back database transaction")

            # Try to rollback filesystem change if possible
            if new_file_path.exists() and not old_file_path.exists():
                try:
                    new_file_path.rename(old_file_path)
                    logger.info(
                        f"Rolled back filesystem rename: {new_filename} -> {old_filename}"
                    )
                except Exception as rollback_error:
                    logger.warning(f"Could not rollback file rename: {rollback_error}")

            raise e
            raise RuntimeError(f"Failed to rename file: {e}") from e

    async def rename_files(
        self, project_name: str, renames: list[dict], db: AsyncSession
    ) -> BulkRenameResponse:
        """Rename multiple files in the project using elan_ids."""
        project_path = safe_project_path(self.base_path, project_name)

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")

        successful_renames = []
        failed_renames = []

        try:
            runner = GitCommandRunner(project_path)

            # Process each rename individually
            for rename_info in renames:
                result = await self._process_single_bulk_rename(
                    rename_info, project_path, db, runner
                )

                if result.success:
                    successful_renames.append(result)
                else:
                    failed_renames.append(result)

            # Commit all changes if any were successful
            commit_hash = await self._finalize_bulk_rename(
                successful_renames, runner, db
            )

            # Count conflicts
            conflicts_count = sum(
                1 for result in failed_renames if result.conflict_elan_id is not None
            )

            # Determine message key based on results
            message_key = None
            if conflicts_count > 0:
                message_key = (
                    "bulk_rename_conflicts"
                    if conflicts_count == len(failed_renames)
                    else "bulk_rename_mixed_errors"
                )
            elif len(failed_renames) > 0:
                message_key = "bulk_rename_errors"
            else:
                message_key = "bulk_rename_success"

            return BulkRenameResponse(
                project_name=project_name,
                total_files=len(renames),
                successful_renames=len(successful_renames),
                failed_renames=len(failed_renames),
                results=successful_renames + failed_renames,
                committed=len(successful_renames) > 0,
                commit_hash=commit_hash,
                renamed_at=datetime.now().isoformat(),
                message=f"Renamed {len(successful_renames)}/{len(renames)} files successfully",
                conflicts_count=conflicts_count,
                message_key=message_key,
            )

        except Exception as e:
            logger.error(f"Critical error during bulk rename: {e!s}")
            await db.rollback()
            raise RuntimeError(f"Bulk rename failed: {e}") from e

    async def _process_single_bulk_rename(
        self,
        rename_info: dict,
        project_path: Path,
        db: AsyncSession,
        runner: GitCommandRunner,
    ) -> RenameResult:
        """Process a single rename operation within a bulk rename."""
        try:
            elan_id = rename_info.get("elan_id")
            new_filename = rename_info.get("new_filename")

            if not elan_id or not new_filename:
                raise ValueError("Missing elan_id or new_filename")

            # Get current filename
            old_filename = await get_elan_file_name_by_id(db, elan_id)
            if not old_filename:
                raise FileNotFoundError(f"ELAN file with ID {elan_id} not found")

            old_file_path = project_path / "elan_files" / old_filename
            new_file_path = project_path / "elan_files" / new_filename

            # Validate file existence and new name availability
            if not old_file_path.exists():
                raise FileNotFoundError(
                    f"File '{old_filename}' not found in filesystem"
                )

            # Check for conflict: if target filename already exists, get its elan_id
            if new_file_path.exists():
                conflict_elan_id = None
                # Get project_id to find the conflicting file
                project_name = project_path.name
                project_id = await get_project_id_by_name(db, project_name)
                if project_id:
                    conflicting_file = await get_elan_file_by_filename_and_project(
                        db, new_filename, project_id
                    )
                    if conflicting_file:
                        conflict_elan_id = conflicting_file.elan_id

                # Raise custom conflict exception with conflict info
                raise RenameConflictError(
                    f"File '{new_filename}' already exists in project",
                    conflict_elan_id=conflict_elan_id,
                    message_key="rename_file_conflict",
                )

            # Update database
            await update_elan_file_name(db, elan_id, new_filename)

            # Rename file
            old_file_path.rename(new_file_path)

            # Stage for git
            runner.add_all()

            return RenameResult(
                old_filename=old_filename,
                new_filename=new_filename,
                success=True,
                error=None,
            )

        except RenameConflictError as e:
            logger.warning(
                f"Rename conflict for elan_id {rename_info.get('elan_id')}: {e!s}"
            )

            # Try to get old filename for error reporting
            old_filename = ""
            try:
                if rename_info.get("elan_id"):
                    old_filename = (
                        await get_elan_file_name_by_id(db, rename_info.get("elan_id"))
                        or ""
                    )
            except Exception:
                logger.warning(
                    f"Could not get filename for elan_id {rename_info.get('elan_id')}"
                )

            return RenameResult(
                old_filename=old_filename,
                new_filename=rename_info.get("new_filename", ""),
                success=False,
                error=str(e),
                conflict_elan_id=e.conflict_elan_id,
                message_key=e.message_key,
            )

        except Exception as e:
            logger.error(
                f"Failed to rename file with elan_id {rename_info.get('elan_id')}: {e!s}"
            )

            # Try to get old filename for error reporting
            old_filename = ""
            try:
                if rename_info.get("elan_id"):
                    old_filename = (
                        await get_elan_file_name_by_id(db, rename_info.get("elan_id"))
                        or ""
                    )
            except Exception:
                logger.warning(
                    f"Could not get filename for elan_id {rename_info.get('elan_id')}"
                )

            return RenameResult(
                old_filename=old_filename,
                new_filename=rename_info.get("new_filename", ""),
                success=False,
                error=str(e),
            )

    async def _finalize_bulk_rename(
        self, successful_renames: list, runner: GitCommandRunner, db: AsyncSession
    ) -> str | None:
        """Finalize the bulk rename operation by committing or rolling back."""
        commit_hash = None
        if successful_renames:
            commit_message = f"Bulk rename: {len(successful_renames)} files"
            commit_hash = runner.commit(commit_message)
            await db.commit()
            logger.info(
                f"Successfully completed bulk rename of {len(successful_renames)} files"
            )
        else:
            await db.rollback()
            logger.warning("No files were successfully renamed")

        return commit_hash

    def command_runner(self, project_name: str) -> GitCommandRunner:
        """Return a path-safe runner for coordination services."""
        return GitCommandRunner(safe_project_path(self.base_path, project_name))
