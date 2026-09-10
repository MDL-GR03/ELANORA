"""Cross-process serialization for mutable Git working trees."""

import asyncio
import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException, Request, status
from filelock import FileLock, Timeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_user_dep
from app.model.project import Project
from app.model.user import User
from app.utils.file_processing import get_elanora_projects_base_path

LOCK_TIMEOUT_SECONDS = 30


def ensure_lock_root(lock_root: Path) -> None:
    """Create the lock directory or return an actionable service error."""
    try:
        lock_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project storage is not writable; contact the instance administrator",
        ) from exc


@asynccontextmanager
async def acquire_project_write_lock(
    project_id: int, projects_root: Path
) -> AsyncIterator[None]:
    """Serialize one project's filesystem mutations across APIs and workers."""
    lock_root = projects_root.resolve() / ".locks"
    ensure_lock_root(lock_root)
    lock_name = hashlib.sha256(str(project_id).encode()).hexdigest()
    lock = FileLock(lock_root / f"{lock_name}.lock")
    try:
        await asyncio.to_thread(lock.acquire, timeout=LOCK_TIMEOUT_SECONDS)
    except Timeout as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Another operation is currently modifying this project",
        ) from exc
    try:
        yield
    finally:
        await asyncio.to_thread(lock.release)


async def project_write_lock(
    request: Request,
    db: AsyncSession = get_db_dep,
    user: User = get_user_dep,
) -> AsyncIterator[None]:
    """Hold a cross-process project lock for the complete request transaction."""
    project_id = request.path_params.get("project_id")
    project_name = request.path_params.get("project_name")
    statement = select(Project)
    if project_id is not None:
        statement = statement.where(Project.project_id == int(project_id))
    elif project_name is not None:
        statement = statement.where(Project.project_name == str(project_name))
    else:
        raise RuntimeError("project_write_lock requires a project path parameter")

    project = (await db.execute(statement)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if project.instance_id != user.instance_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    async with acquire_project_write_lock(
        project.project_id, Path(get_elanora_projects_base_path())
    ):
        yield
