"""Read and resolution operations for immutable accepted project history."""

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project_by_name
from app.model.project_revision import ProjectRevision
from app.model.user import User
from app.service.git_operations import GitCommandRunner


class ProjectHistoryService:
    """Build accepted-history responses from the authoritative revision ledger."""

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
