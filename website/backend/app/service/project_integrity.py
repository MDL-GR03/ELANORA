"""Integrity checks and recovery for authoritative project revisions."""

import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.elan_file import get_elan_files_by_project
from app.crud.project import get_project_by_name
from app.elan import parse_eaf
from app.elan.persistence import document_to_persistence
from app.elan.validation import validate_eaf
from app.model.association import UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import ProjectPermission, UserRole
from app.model.notification import Notification
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.model.project_revision import ProjectRevision
from app.model.user import User
from app.service.elan import ElanService
from app.service.git_operations import GitCommandRunner
from app.service.project_revision import verify_project_revision_manifest
from app.storage.paths import safe_project_path

MIN_RECOVERY_REASON_LENGTH = 10


class ProjectIntegrityService:
    """Keep derived project state consistent with immutable revision manifests."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

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
        if revision.revision_id != project.current_revision_id:
            raise ValueError(
                "Only the current accepted project revision can be rebuilt"
            )
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
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
        revision = (
            await db.get(ProjectRevision, project.current_revision_id)
            if project.current_revision_id is not None
            else None
        )
        if revision is None:
            return {
                "project_name": project_name,
                "git_commit": git_commit,
                "status": "ledger_missing",
                "recoverable": False,
                "git_export_matches": False,
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
                "git_export_matches": git_commit == revision.git_commit,
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
            "git_export_matches": git_commit == revision.git_commit,
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
            "git_export_matches",
        )
        result["status"] = (
            "recovery_required"
            if any(
                not result[key] if key == "git_export_matches" else result[key]
                for key in issue_keys
            )
            else "healthy"
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
        if project.current_revision_id != revision.revision_id:
            raise ValueError(
                "Only the current accepted project revision can be recovered"
            )

        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        previous_git_head = runner.get_commit_hash()
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
                # Git is a compatibility export of the authoritative database
                # revision. Re-anchor it before materializing the immutable
                # manifest so an accidentally advanced checkout is repairable.
                if previous_git_head != revision.git_commit:
                    runner.reset_hard(revision.git_commit)
                for path in elan_directory.glob("*.eaf"):
                    path.unlink()
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
                if runner.get_commit_hash() != previous_git_head:
                    runner.reset_hard(previous_git_head)
                for path in elan_directory.glob("*.eaf"):
                    path.unlink()
                for path in backup_directory.glob("*.eaf"):
                    path.replace(elan_directory / path.name)
                raise

        return {**rebuilt, "status": "recovered"}
