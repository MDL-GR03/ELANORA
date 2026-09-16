"""Cross-process serialization for mutable Git working trees."""

import asyncio
import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Request
from filelock import FileLock, Timeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
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
        raise ElanoraError(ErrorCode.STORAGE_NOT_WRITABLE) from exc


@asynccontextmanager
async def acquire_project_write_lock(
    project_id: int, projects_root: Path
) -> AsyncIterator[None]:
    """Serialize one project's filesystem mutations across APIs and workers."""
    lock_root = projects_root.resolve() / ".locks"
    ensure_lock_root(lock_root)
    lock_name = hashlib.sha256(str(project_id).encode()).hexdigest()
    # Acquire and release each run through asyncio.to_thread, which may hand
    # them to different executor threads. FileLock is thread-local by default,
    # so a release on another thread silently does nothing: the descriptor
    # leaks and the project stays locked until the process restarts. This lock
    # object is used by exactly one coroutine, so sharing its state is safe.
    lock = FileLock(lock_root / f"{lock_name}.lock", thread_local=False)
    try:
        await asyncio.to_thread(lock.acquire, timeout=LOCK_TIMEOUT_SECONDS)
    except Timeout as exc:
        raise ElanoraError(ErrorCode.PROJECT_LOCKED) from exc
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
        raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)
    if project.instance_id != user.instance_id:
        raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)

    async with acquire_project_write_lock(
        project.project_id, Path(get_elanora_projects_base_path())
    ):
        yield
