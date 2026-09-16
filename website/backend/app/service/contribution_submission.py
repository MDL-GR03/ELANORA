"""Submitting researcher EAF files as a contribution awaiting review.

A submission branches from the accepted project, writes the uploaded files,
and durably records the resulting tree as a pending contribution. Only then
may project policy accept it automatically. From the moment it is recorded the
contribution exists, so a later failure must never be reported as a failed
upload.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.project import get_project_by_id
from app.schema.protocol import ProtocolRules
from app.service.contribution_intake import (
    ContributionAlreadyCurrentError,
    ContributionIntakeService,
    DuplicatePendingContributionError,
    SubmissionContext,
)
from app.service.git_branches import GitBranchManager, GitDiffAnalyzer
from app.service.git_command_runner import GitCommandRunner
from app.service.git_uploads import FileUploadProcessor
from app.service.protocol_shared import get_pinned_protocol_version
from app.service.upload_naming_compliance import enforce_upload_naming_standard
from app.storage.paths import safe_project_path

logger = get_logger()

# Publishes a recorded contribution: (project_name, branch_name, db, user_id).
AcceptContribution = Callable[[str, str, AsyncSession, int], Awaitable[Any]]


class ContributionSubmissionService:
    """Turn uploaded EAF files into a recorded, reviewable contribution."""

    def __init__(
        self,
        base_path: Path,
        intake: ContributionIntakeService,
        accept: AcceptContribution,
    ) -> None:
        self.base_path = base_path
        self.intake = intake
        self.accept = accept

    async def submit(
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
        """Record uploaded files as a pending contribution on a review branch."""
        project = await get_project_by_id(db, project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")
        # Read now. A failed automatic acceptance rolls the session back, which
        # expires ORM attributes; reading them afterwards cannot lazy-load here.
        project_name = project.project_name
        auto_accept_new_files = bool(project.auto_accept_new_files)

        project_path = safe_project_path(self.base_path, project_name)
        protocol_version = await get_pinned_protocol_version(db, project)
        await enforce_upload_naming_standard(
            db,
            project_id,
            [file.filename for file in files],
            protocol_rules=(
                None
                if protocol_version is None
                else ProtocolRules.model_validate(protocol_version.rules)
            ),
        )
        self.intake.validate_request(project_path, files)

        branch_name: str | None = None
        contribution_recorded = False
        try:
            self.intake.configure_git_user(project_path, user_name)
            branch_manager = GitBranchManager(project_path)
            file_processor = FileUploadProcessor(project_path)
            diff_analyzer = GitDiffAnalyzer(project_path)

            branch_manager.switch_to_master()
            # Judged against the accepted project, after the switch: the working
            # tree may have been left on another branch by an administrator.
            existing_files = self.intake.existing_files(project_path, files)
            base_commit = GitCommandRunner(
                project_path, maintain_backup=False
            ).get_commit_hash()
            branch_name = branch_manager.create_upload_branch(user_name, len(files))
            uploaded_files, failed_files = await file_processor.process_files(
                files, existing_files
            )
            if not uploaded_files:
                raise RuntimeError("No files were successfully uploaded")

            file_processor.commit_files(uploaded_files, user_name)
            upload_info = await self.intake.record_pending_submission(
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
        except (DuplicatePendingContributionError, ContributionAlreadyCurrentError):
            if branch_name and not contribution_recorded:
                self.intake.discard_failed_submission(project_path, branch_name)
            raise
        except Exception as error:
            if branch_name and not contribution_recorded:
                self.intake.discard_failed_submission(project_path, branch_name)
            logger.error(
                "Batch ELAN file operation failed; error_type=%s",
                safe_exception_type(error),
            )
            raise RuntimeError("Failed to add ELAN files") from error

        upload_info["auto_accepted"] = await self._accept_if_policy_allows(
            db,
            project_name=project_name,
            auto_accept_new_files=auto_accept_new_files,
            upload_info=upload_info,
            has_failed_files=bool(failed_files),
            user_id=user_id,
        )
        logger.info("Successfully processed a project upload")
        return self.intake.build_response(
            project_name, uploaded_files, failed_files, upload_info
        )

    async def _accept_if_policy_allows(
        self,
        db: AsyncSession,
        *,
        project_name: str,
        auto_accept_new_files: bool,
        upload_info: dict[str, Any],
        has_failed_files: bool,
        user_id: int,
    ) -> bool:
        """Accept a purely additive contribution when project policy allows it.

        The contribution is already recorded. Any failure here leaves it pending
        for an administrator and must not turn into a failed upload.
        """
        if (
            not auto_accept_new_files
            or upload_info["modified_files"]
            or upload_info["deleted_files"]
            or has_failed_files
        ):
            return False
        try:
            await self.accept(project_name, upload_info["branch_name"], db, user_id)
        except Exception as error:
            await db.rollback()
            logger.error(
                "Automatic acceptance failed; contribution remains pending; "
                "error_type=%s",
                safe_exception_type(error),
            )
            return False
        upload_info["status"] = "accepted_automatically"
        upload_info["message"] = (
            "The valid new files were accepted automatically by project policy."
        )
        return True
