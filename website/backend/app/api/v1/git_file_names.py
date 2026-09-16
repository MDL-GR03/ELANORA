"""Renaming accepted files."""

from fastapi import APIRouter, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import git_shared
from app.core.exceptions import RenameConflictError
from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_write_dep,
)
from app.schema.requests.git import (
    BulkRenameRequest,
)
from app.schema.responses.git import (
    BulkRenameResponse,
    FileRenameResponse,
)

router = APIRouter()


@router.post(
    "/projects/{project_name}/rename-file",
    response_model=FileRenameResponse,
    dependencies=[get_project_write_dep, git_shared.project_lock_dep],
)
async def rename_file(
    project_name: str,
    elan_id: int = Form(...),
    new_filename: str = Form(...),
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> FileRenameResponse:
    """Rename a single file in the project."""
    try:
        result = await git_shared.git_service.rename_file(
            project_name=project_name,
            elan_id=elan_id,
            new_filename=new_filename,
            db=db,
        )
        return result
    except RenameConflictError as e:
        # Return conflict info with 409 status code
        return FileRenameResponse(
            project_name=project_name,
            old_filename="",  # Will be filled by service if needed
            new_filename=new_filename,
            success=False,
            committed=False,
            commit_hash=None,
            renamed_at="",
            message="A file with the target name already exists",
            conflict_elan_id=e.conflict_elan_id,
            message_key=e.message_key,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/rename-files",
    response_model=BulkRenameResponse,
    dependencies=[get_project_write_dep, git_shared.project_lock_dep],
)
async def rename_files(
    project_name: str,
    request: BulkRenameRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> BulkRenameResponse:
    """Rename multiple files in the project."""
    try:
        renames = [
            {"elan_id": rename.elan_id, "new_filename": rename.new_filename}
            for rename in request.renames
        ]
        result = await git_shared.git_service.rename_files(
            project_name=project_name,
            renames=renames,
            db=db,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
