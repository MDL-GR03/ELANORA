from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.dependency.project_lock import ensure_lock_root


def test_ensure_lock_root_reports_unwritable_project_storage() -> None:
    with (
        patch.object(Path, "mkdir", side_effect=PermissionError("read-only")),
        pytest.raises(HTTPException) as error,
    ):
        ensure_lock_root(Path("/project-storage/.locks"))

    assert error.value.status_code == 503
    assert "not writable" in str(error.value.detail)
