from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_PROJECTS_BASE_PATH
from app.crud import elan_file_media as elan_media_crud
from app.crud.elan_file import (
    get_elan_files_by_project,
)
from app.crud.project import (
    get_project_by_name,
    list_projects_by_instance,
    list_projects_by_user,
)
from app.elan.validation import validate_eaf
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.enums import ProjectPermission
from app.schema.responses.contribution_queue import ReviewQueueResponse
from app.schema.responses.git import (
    BulkRenameResponse,
    FileRenameResponse,
    ProjectInfo,
    ProjectSyncCheckResponse,
)
from app.service.contribution_inspection import ContributionInspectionService
from app.service.contribution_intake import (
    ContributionIntakeService,
)
from app.service.contribution_publication import ContributionPublicationService
from app.service.contribution_queue import ContributionQueueService
from app.service.contribution_review import ContributionReviewService
from app.service.contribution_submission import ContributionSubmissionService
from app.service.elan import ElanService
from app.service.file_rename import FileRenameService
from app.service.git_command_runner import GitCommandRunner
from app.service.project_filesystem_sync import ProjectFilesystemSyncService
from app.service.project_history import ProjectHistoryService, ProjectRestoreCommand
from app.service.project_integrity import ProjectIntegrityService
from app.service.project_lifecycle import ProjectLifecycleService
from app.service.project_recovery import ProjectRecoveryService
from app.storage.paths import safe_project_path

logger = get_logger()
MIN_RECOVERY_REASON_LENGTH = 10
MIN_NAME_STATUS_FIELDS = 2


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
        self.project_history = ProjectHistoryService(self.base_path)
        self.project_integrity = ProjectIntegrityService(self.base_path)
        self.project_lifecycle = ProjectLifecycleService(self.base_path)
        self.contribution_intake = ContributionIntakeService()
        self.contribution_inspection = ContributionInspectionService(self.base_path)
        self.contribution_review = ContributionReviewService(
            self.base_path, self.contribution_inspection
        )
        self.contribution_publication = ContributionPublicationService(
            self.base_path, self.contribution_review
        )
        self.contribution_queue = ContributionQueueService(
            self.base_path, self.contribution_inspection
        )
        self.contribution_submission = ContributionSubmissionService(
            self.base_path,
            self.contribution_intake,
            accept=self._accept_automatically,
        )
        self.file_rename = FileRenameService(self.base_path)
        self.filesystem_sync = ProjectFilesystemSyncService(self.base_path)
        self.project_recovery = ProjectRecoveryService(
            self.base_path, self.filesystem_sync
        )

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

    async def get_accepted_project_history(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """List published states from the authoritative revision ledger."""
        return await self.project_history.list_accepted_versions(project_name, db)

    async def preview_project_version_restore(
        self, project_name: str, target_commit: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Preview files, EAF meaning, and open work affected by a restoration."""
        return await self.project_history.preview_restore(
            project_name, target_commit, db
        )

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
        return await self.project_history.restore(
            ProjectRestoreCommand(
                project_name=project_name,
                target_commit=target_commit,
                expected_head=expected_head,
                reason=reason,
                confirmation=confirmation,
                user_id=user_id,
                actor_name=actor_name,
            ),
            db,
            self.rebuild_project_database,
        )

    async def create_project(
        self,
        project_name: str,
        description: str | None,
        db: AsyncSession,
        user_id: int,
        instance_id: int,
    ) -> dict[str, Any]:
        """Create a new project with Git repository and description."""
        return await self.project_lifecycle.create_project(
            project_name,
            description,
            db,
            user_id,
            instance_id,
        )

    async def add_elan_files(
        self,
        project_id: int,
        files: list[UploadFile],
        db: AsyncSession,
        user_id: int,
        user_name: str,
        protocol_validation: dict[str, object],
        research_context: dict[str, Any] | None = None,
        allow_current_tree: bool = False,
    ) -> dict[str, Any]:
        """Add multiple ELAN files to the project with branch-based workflow."""
        return await self.contribution_submission.submit(
            project_id,
            files,
            db,
            user_id,
            user_name,
            protocol_validation,
            research_context=research_context,
            allow_current_tree=allow_current_tree,
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
        permissions: dict[int, ProjectPermission] = {}
        for project_id, permission in permission_rows.tuples():
            permissions[project_id] = permission
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
    ) -> dict[str, Any]:
        """Initialize a project atomically from uploaded EAF files."""
        return await self.project_lifecycle.import_project(
            project_name,
            description,
            files,
            db,
            user_id,
            instance_id,
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
        return await self.project_integrity.rebuild_current_revision_projection(
            project_name,
            revision_id,
            db,
            user_id,
            commit_changes=commit_changes,
        )

    async def get_current_revision_health(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Compare the accepted ledger with disk and the mutable DB projection."""
        return await self.project_integrity.get_current_revision_health(
            project_name, db
        )

    async def record_current_revision_health(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Persist a scan and notify administrators only on health transitions."""
        return await self.project_integrity.record_current_revision_health(
            project_name, db
        )

    async def scan_all_project_integrity(
        self, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Scan every active project without repairing or rewriting project data."""
        return await self.project_integrity.scan_all_project_integrity(db)

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
        return await self.project_integrity.recover_current_revision_from_manifest(
            project_name,
            revision_id,
            db,
            user_id,
            reason=reason,
            confirmation=confirmation,
        )

    async def get_pending_uploads_with_status(
        self, project_name: str, db: AsyncSession
    ) -> ReviewQueueResponse:
        """Get pending uploads and compute their merge readiness in real-time."""
        return await self.contribution_queue.review_queue(project_name, db)

    def test_pending_upload(
        self, project_name: str, branch_name: str
    ) -> dict[str, Any]:
        """Test a contribution without changing accepted project state."""
        return self.contribution_inspection.test_compatibility(
            project_name, branch_name
        )

    async def set_contribution_research_topic(
        self,
        project_name: str,
        upload_id: int,
        topic_id: int | None,
        new_topic_name: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Resolve a contribution's topic while retaining its declared evidence."""
        return await self.contribution_review.assign_research_topic(
            project_name, upload_id, topic_id, new_topic_name, db
        )

    async def _accept_automatically(
        self, project_name: str, branch_name: str, db: AsyncSession, user_id: int
    ) -> None:
        """Publish a contribution accepted by project policy rather than a person."""
        await self.complete_pending_upload(
            project_name, branch_name, "auto", db, user_id
        )

    async def complete_pending_upload(
        self,
        project_name: str,
        branch_name: str,
        resolution_strategy: str,
        db: AsyncSession,
        user_id: int,
        expected_parent_commit: str | None = None,
    ) -> dict[str, Any]:
        """Merge a reviewed contribution, synchronize it, and close its queue record."""

        async def rebuild_projection(
            name: str, session: AsyncSession, actor_user_id: int
        ) -> None:
            await self.rebuild_project_database(
                name, session, actor_user_id, commit_changes=False
            )

        return await self.contribution_publication.publish(
            project_name,
            branch_name,
            resolution_strategy,
            db,
            user_id,
            rebuild_projection,
            expected_parent_commit,
        )

    async def dismiss_duplicate_upload(
        self,
        project_name: str,
        upload_id: int,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Dismiss a verified duplicate while retaining its audit record."""
        return await self.contribution_review.dismiss_duplicate(
            project_name, upload_id, db, user_id
        )

    async def decline_pending_upload(
        self,
        project_name: str,
        upload_id: int,
        reason: str,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Terminally decline pending work without erasing its audit history."""
        return await self.contribution_review.decline(
            project_name, upload_id, reason, db, user_id
        )

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
            raise RuntimeError("Failed to get branches") from e

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
            logger.debug("Retrieving project file metadata")

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

        logger.info("Retrieved %s project files", len(enriched_files))
        return {"files": enriched_files}

    async def synchronize_project(
        self,
        project_name: str,
        db: AsyncSession,
        user_id: int,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Idempotently synchronize the project's elan_files with the database."""
        return await self.filesystem_sync.synchronize(
            project_name, db, user_id, operation_id
        )

    def validate_sync_changes(
        self, project_name: str, changes: list[dict[str, object]]
    ) -> None:
        """Apply the canonical EAF preflight to a serialized preview."""
        self.filesystem_sync.validate_changes(project_name, changes)

    async def delete_project(self, project_name: str, db: AsyncSession) -> None:
        """Retain the project record as deleted, then remove its working folder."""
        await self.project_lifecycle.delete_project(db, project_name)

    async def edit_project(
        self,
        old_project_name: str,
        new_project_name: str,
        new_project_description: str | None,
        db: AsyncSession,
    ) -> dict[str, str | None]:
        """Rename a project and update its description as one change."""
        return await self.project_lifecycle.rename_project(
            db, old_project_name, new_project_name, new_project_description
        )

    def synchronize_project_check(self, project_name: str) -> ProjectSyncCheckResponse:
        """Check for changes in a Git-managed project and analyze file status."""
        return self.filesystem_sync.inspect_project(project_name)

    def discard_local_changes(self, project_name: str) -> str:
        """Reset the project folder to the latest canonical Git state."""
        return self.filesystem_sync.discard_local_changes(project_name)

    async def restore_project_from_backup(
        self, project_name: str, db: AsyncSession, user_id: int
    ) -> str:
        """Restore a project's missing storage from its recovery backup."""
        return await self.project_recovery.restore_from_backup(
            db, project_name, user_id
        )

    async def decline_project_backup(self, db: AsyncSession, project_name: str) -> None:
        """Delete a project with missing storage, together with its backup."""
        await self.project_recovery.discard(db, project_name)

    async def rename_file(
        self, project_name: str, elan_id: int, new_filename: str, db: AsyncSession
    ) -> FileRenameResponse:
        """Rename a single file in the project using elan_id."""
        return await self.file_rename.rename_one(
            db, project_name, elan_id, new_filename
        )

    async def rename_files(
        self, project_name: str, renames: list[dict[str, Any]], db: AsyncSession
    ) -> BulkRenameResponse:
        """Rename multiple files in the project using elan_ids."""
        return await self.file_rename.rename_many(db, project_name, renames)

    def command_runner(self, project_name: str) -> GitCommandRunner:
        """Return a path-safe runner for coordination services."""
        return GitCommandRunner(safe_project_path(self.base_path, project_name))
