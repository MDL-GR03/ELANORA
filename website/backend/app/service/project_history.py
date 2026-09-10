"""Read and resolution operations for immutable accepted project history."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.pending_upload import get_pending_uploads
from app.crud.project import get_project_by_name
from app.elan import compare_eaf, parse_eaf
from app.elan.validation import validate_eaf
from app.model.audit_event import AuditEvent
from app.model.enums import ReviewCaseState
from app.model.notification import Notification
from app.model.project_revision import ProjectRevision
from app.model.review import ReviewCase
from app.model.user import User
from app.service.git_operations import GitCommandRunner
from app.service.project_revision import append_project_revision
from app.storage.paths import safe_project_path
from app.utils.project_backup import update_backup

MIN_NAME_STATUS_FIELDS = 2
ProjectionRebuilder = Callable[..., Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ProjectRestoreCommand:
    project_name: str
    target_commit: str
    expected_head: str
    reason: str
    confirmation: str
    user_id: int
    actor_name: str | None = None


class ProjectHistoryService:
    """Build accepted-history responses from the authoritative revision ledger."""

    def __init__(
        self,
        base_path: Path | None = None,
    ) -> None:
        self.base_path = base_path

    def _project_path(self, project_name: str) -> Path:
        if self.base_path is None:
            raise RuntimeError(
                "Project history filesystem operations are not configured"
            )
        return safe_project_path(self.base_path, project_name)

    @staticmethod
    def canonical_commits(runner: GitCommandRunner) -> list[str]:
        """Return compatibility-export commits from the canonical first parent."""
        result = runner.run(
            ["rev-list", "--first-parent", runner.canonical_branch()], check=True
        )
        return [line for line in result.stdout.splitlines() if line]

    def resolve_export_commit(
        self, runner: GitCommandRunner, target_commit: str
    ) -> tuple[str, list[str]]:
        """Resolve a safe accepted-history Git export identifier."""
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", target_commit):
            raise ValueError("Invalid project version")
        resolved = runner.run(
            ["rev-parse", "--verify", f"{target_commit}^{{commit}}"], check=False
        )
        if resolved.returncode != 0:
            raise ValueError("Project version not found")
        commit = resolved.stdout.strip()
        canonical = self.canonical_commits(runner)
        if commit not in canonical:
            raise ValueError("The selected version is not in accepted project history")
        return commit, canonical

    async def list_accepted_versions(
        self, project_name: str, db: AsyncSession
    ) -> dict[str, Any]:
        """List published states without deriving workflow state from Git."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        rows = (
            await db.execute(
                select(ProjectRevision, User.username)
                .outerjoin(User, User.user_id == ProjectRevision.actor_user_id)
                .where(ProjectRevision.project_id == project.project_id)
                .order_by(ProjectRevision.ordinal.desc())
            )
        ).all()
        versions = [
            self._version_payload(
                revision,
                actor_name,
                is_current=revision.revision_id == project.current_revision_id,
            )
            for revision, actor_name in rows
        ]
        return {
            "project_name": project_name,
            "current_commit": next(
                (version["commit"] for version in versions if version["is_current"]),
                "",
            ),
            "versions": versions,
        }

    async def preview_restore(
        self, project_name: str, target_commit: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Preview files, EAF meaning, and open work affected by a restoration."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        runner = GitCommandRunner(self._project_path(project_name))
        target, _ = self.resolve_export_commit(runner, target_commit)
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
        review_rows = list(
            (
                await db.scalars(
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
            ).all()
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

    async def restore(
        self,
        command: ProjectRestoreCommand,
        db: AsyncSession,
        rebuild_projection: ProjectionRebuilder | None = None,
    ) -> dict[str, Any]:
        """Restore an accepted tree as a new immutable project revision."""
        project_name = command.project_name
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        if command.confirmation != f"RESTORE {project_name}":
            raise ValueError(f'Type "RESTORE {project_name}" to confirm')
        runner = GitCommandRunner(self._project_path(project_name))
        runner.checkout(runner.canonical_branch())
        previous = runner.get_commit_hash()
        if previous != command.expected_head:
            raise ValueError(
                "Accepted project history changed. Refresh the preview before restoring"
            )
        target, _ = self.resolve_export_commit(runner, command.target_commit)
        if target == previous:
            raise ValueError("The selected version is already current")
        if runner.run(["status", "--porcelain"], check=True).stdout.strip():
            raise ValueError("The project working tree is not clean")
        eaf_paths = runner.run(
            ["ls-tree", "-r", "--name-only", target, "--", "elan_files"], check=True
        ).stdout.splitlines()
        for filename in eaf_paths:
            if filename.lower().endswith(".eaf"):
                validate_eaf(
                    runner.run_bytes(
                        ["show", f"{target}:{filename}"], check=True
                    ).stdout
                )
        runner.run(["read-tree", "--reset", "-u", f"{target}^{{tree}}"], check=True)
        commit_args = [
            "commit",
            "-m",
            f"Restore accepted project version {target[:8]}",
            "-m",
            f"Reason: {command.reason.strip()}",
        ]
        if command.actor_name:
            safe_email_name = re.sub(r"[^a-z0-9._-]+", "-", command.actor_name.lower())
            commit_args = [
                "-c",
                f"user.name={command.actor_name}",
                "-c",
                f"user.email={safe_email_name}@elanora.local",
                *commit_args,
            ]
        runner.run(commit_args, check=True)
        restored = runner.get_commit_hash()
        try:
            if rebuild_projection is None:
                raise RuntimeError("Project history restoration is not configured")
            await rebuild_projection(
                project_name, db, command.user_id, commit_changes=False
            )
            db.add(
                AuditEvent(
                    actor_user_id=command.user_id,
                    project_id=project.project_id,
                    action="project.version.restored",
                    resource_type="project",
                    resource_id=str(project.project_id),
                    details={
                        "previous_commit": previous,
                        "target_commit": target,
                        "restored_commit": restored,
                        "reason": command.reason.strip(),
                    },
                )
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=restored,
                parent_git_commit=previous,
                source_type="restoration",
                actor_user_id=command.user_id,
                details={"target_commit": target, "reason": command.reason.strip()},
            )
            pending = await get_pending_uploads(db, project.project_id)
            notified_users = {
                upload.submitted_by
                for upload in pending
                if upload.submitted_by not in {None, command.user_id}
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
        project_path = self._project_path(project_name)
        update_backup(project_path.name, project_path.parent)
        return {
            "project_name": project_name,
            "previous_commit": previous,
            "target_commit": target,
            "restored_commit": restored,
            "status": "restored_as_new_version",
        }

    @staticmethod
    def _version_payload(
        revision: ProjectRevision,
        actor_name: str | None,
        *,
        is_current: bool,
    ) -> dict[str, Any]:
        details = revision.details
        contribution_id = revision.contribution_id
        action = {
            "contribution": "contribution.accepted",
            "restoration": "project.version.restored",
            "migration": "project.revision.migrated",
        }[revision.source_type]
        if contribution_id is not None:
            message = f"Accepted contribution #{contribution_id}"
        elif revision.source_type == "restoration":
            target = str(details.get("target_commit", ""))[:8]
            message = f"Restored project to version {target}"
        else:
            message = str(details.get("message") or "Initial project revision")
        return {
            "commit": revision.git_commit,
            "short_commit": revision.git_commit[:8],
            "committed_at": revision.created_at.isoformat(),
            "message": message,
            "author": actor_name or "ELANORA",
            "action": action,
            "contribution_id": contribution_id,
            "restored_from": details.get("target_commit"),
            "reason": details.get("reason"),
            "is_current": is_current,
        }
