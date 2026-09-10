"""Durable coordination of exceptional server-side project imports."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project_by_name
from app.model.audit_event import AuditEvent
from app.model.project_sync_operation import ProjectSyncOperation
from app.service.project_revision import append_project_revision
from app.storage.paths import safe_project_path
from app.storage.sync_evidence import SyncEvidenceStore

if TYPE_CHECKING:
    from app.service.git import GitService


class ProjectSyncCoordinator:
    """A saga coordinator whose durable states make partial completion visible."""

    def __init__(
        self, git_service: "GitService", evidence_store: SyncEvidenceStore | None = None
    ) -> None:
        self.git = git_service
        self.evidence = evidence_store or SyncEvidenceStore()

    async def execute(
        self, project_name: str, db: AsyncSession, user_id: int
    ) -> ProjectSyncOperation:
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        preview = self.git.synchronize_project_check(project_name)
        changes = [dict(item) for item in preview.get("files_status", [])]
        runner = self.git.command_runner(project_name)
        operation = ProjectSyncOperation(
            project_id=project.project_id,
            initiated_by=user_id,
            state="preparing",
            changes=changes,
            starting_commit=runner.get_commit_hash(),
        )
        db.add(operation)
        await db.commit()
        try:
            project_path = safe_project_path(self.git.base_path, project_name)
            staging_key, manifest = self.evidence.preserve(
                operation.operation_id, project_path, changes
            )
            self.git.validate_sync_changes(project_name, changes)
            operation.staging_key = staging_key
            operation.evidence_manifest = manifest
            operation.state = "prepared"
            await db.commit()
            operation.state = "committing"
            await db.commit()
            await self.git.synchronize_project(
                project_name, db, user_id, operation_id=str(operation.operation_id)
            )
            operation.resulting_commit = runner.get_commit_hash()
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=operation.resulting_commit,
                parent_git_commit=operation.starting_commit,
                source_type="migration",
                actor_user_id=user_id,
                details={
                    "message": "Accepted administrator-imported server changes",
                    "sync_operation_id": str(operation.operation_id),
                },
            )
            operation.state = "completed"
            operation.completed_at = datetime.now(UTC)
            operation.evidence_expires_at = datetime.now(UTC) + timedelta(days=30)
            self._add_audit(db, operation, "project.server_sync.completed")
            await db.commit()
            return operation
        except BaseException as error:
            await db.rollback()
            operation = await db.get(ProjectSyncOperation, operation.operation_id)
            if operation is not None:
                head = runner.get_commit_hash()
                operation.state = (
                    "recovery_required"
                    if head != operation.starting_commit
                    else "failed"
                )
                operation.resulting_commit = (
                    head if head != operation.starting_commit else None
                )
                operation.error = str(error)[:4000]
                self._add_audit(db, operation, f"project.server_sync.{operation.state}")
                await db.commit()
            raise

    async def list_for_project(
        self, project_name: str, db: AsyncSession
    ) -> list[ProjectSyncOperation]:
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        result = await db.execute(
            select(ProjectSyncOperation)
            .where(ProjectSyncOperation.project_id == project.project_id)
            .order_by(ProjectSyncOperation.created_at.desc())
            .limit(50)
        )
        operations = list(result.scalars())
        changed = False
        now = datetime.now(UTC)
        for operation in operations:
            if operation.state in {"preparing", "prepared"}:
                operation.state = "failed"
                operation.error = (
                    "The process stopped before changing canonical Git history"
                )
                self._add_audit(db, operation, "project.server_sync.failed")
                changed = True
            elif operation.state == "committing":
                runner = self.git.command_runner(project_name)
                head = runner.get_commit_hash()
                operation.state = (
                    "recovery_required"
                    if head != operation.starting_commit
                    else "failed"
                )
                operation.error = "The process stopped before recording a final outcome"
                operation.resulting_commit = (
                    head if head != operation.starting_commit else None
                )
                self._add_audit(db, operation, f"project.server_sync.{operation.state}")
                changed = True
            if (
                operation.state == "completed"
                and operation.staging_key
                and operation.evidence_expires_at
                and operation.evidence_expires_at <= now
            ):
                self.evidence.discard(operation.staging_key)
                operation.staging_key = None
                changed = True
        if changed:
            await db.commit()
        return operations

    async def recover(
        self, project_name: str, operation_id: uuid.UUID, db: AsyncSession, user_id: int
    ) -> ProjectSyncOperation:
        """Complete a Git-committed saga by rebuilding its database projection."""
        project = await get_project_by_name(db, project_name)
        operation = await db.get(ProjectSyncOperation, operation_id)
        if (
            project is None
            or operation is None
            or operation.project_id != project.project_id
        ):
            raise FileNotFoundError("Synchronization operation not found")
        if operation.state != "recovery_required":
            raise ValueError("Only recovery-required operations can be recovered")
        runner = self.git.command_runner(project_name)
        head = runner.get_commit_hash()
        commit_message = runner.run(["log", "-1", "--format=%B"], check=True).stdout
        if (
            operation.resulting_commit != head
            and str(operation.operation_id) not in commit_message
        ):
            raise ValueError("Canonical Git history does not match this operation")
        await self.git.rebuild_project_database(project_name, db, user_id)
        await append_project_revision(
            db,
            project_id=project.project_id,
            git_commit=head,
            parent_git_commit=operation.starting_commit,
            source_type="migration",
            actor_user_id=user_id,
            details={
                "message": "Recovered administrator-imported server changes",
                "sync_operation_id": str(operation.operation_id),
            },
        )
        operation.state = "completed"
        operation.resulting_commit = head
        operation.error = None
        operation.completed_at = datetime.now(UTC)
        operation.evidence_expires_at = datetime.now(UTC) + timedelta(days=30)
        self._add_audit(db, operation, "project.server_sync.recovered")
        await db.commit()
        return operation

    async def discard(
        self, project_name: str, db: AsyncSession, user_id: int
    ) -> ProjectSyncOperation:
        """Preserve evidence, then discard exceptional server-side changes."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        preview = self.git.synchronize_project_check(project_name)
        changes = [dict(item) for item in preview.get("files_status", [])]
        runner = self.git.command_runner(project_name)
        operation = ProjectSyncOperation(
            project_id=project.project_id,
            initiated_by=user_id,
            state="preparing",
            changes=changes,
            starting_commit=runner.get_commit_hash(),
        )
        db.add(operation)
        await db.commit()
        try:
            project_path = safe_project_path(self.git.base_path, project_name)
            staging_key, manifest = self.evidence.preserve(
                operation.operation_id, project_path, changes
            )
            operation.staging_key = staging_key
            operation.evidence_manifest = manifest
            operation.state = "prepared"
            await db.commit()
            self.git.discard_local_changes(project_name)
            operation.state = "discarded"
            operation.completed_at = datetime.now(UTC)
            operation.evidence_expires_at = datetime.now(UTC) + timedelta(days=30)
            self._add_audit(db, operation, "project.server_sync.discarded")
            await db.commit()
            return operation
        except BaseException as error:
            await db.rollback()
            operation = await db.get(ProjectSyncOperation, operation.operation_id)
            if operation is not None:
                operation.state = "failed"
                operation.error = str(error)[:4000]
                self._add_audit(db, operation, "project.server_sync.failed")
                await db.commit()
            raise

    @staticmethod
    def _add_audit(
        db: AsyncSession, operation: ProjectSyncOperation, action: str
    ) -> None:
        db.add(
            AuditEvent(
                actor_user_id=operation.initiated_by,
                project_id=operation.project_id,
                action=action,
                resource_type="project_sync_operation",
                resource_id=str(operation.operation_id),
                details={
                    "state": operation.state,
                    "starting_commit": operation.starting_commit,
                    "resulting_commit": operation.resulting_commit,
                    "changed_files": len(operation.changes),
                },
            )
        )


def operation_payload(operation: ProjectSyncOperation) -> dict[str, Any]:
    return {
        "operation_id": str(operation.operation_id),
        "state": operation.state,
        "changes": operation.changes,
        "evidence_manifest": operation.evidence_manifest,
        "starting_commit": operation.starting_commit,
        "resulting_commit": operation.resulting_commit,
        "error": operation.error,
        "created_at": operation.created_at,
        "completed_at": operation.completed_at,
        "evidence_expires_at": operation.evidence_expires_at,
    }
