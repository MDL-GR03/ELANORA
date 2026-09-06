"""Protected, content-hashed evidence storage for server synchronization runs."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from app.core.settings import get_settings


class SyncEvidenceStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().sync_staging_base_path).resolve()

    def preserve(
        self,
        operation_id: uuid.UUID,
        project_root: Path,
        changes: list[dict[str, object]],
    ) -> tuple[str, list[dict[str, object]]]:
        operation_root = (self.root / str(operation_id)).resolve()
        if operation_root.parent != self.root:
            raise ValueError("Invalid synchronization operation key")
        operation_root.mkdir(parents=True, exist_ok=False, mode=0o700)
        manifest: list[dict[str, object]] = []
        for change in changes:
            relative = Path(str(change["filename"]))
            source = (project_root / relative).resolve()
            if project_root.resolve() not in source.parents:
                raise ValueError("Synchronization evidence path escapes project")
            item: dict[str, object] = {
                "filename": relative.as_posix(),
                "status": str(change["status"]),
            }
            if source.is_file():
                content = source.read_bytes()
                target = operation_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                item.update(
                    {
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "size": len(content),
                    }
                )
            manifest.append(item)
        (operation_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        return str(operation_id), manifest

    def discard(self, key: str) -> None:
        """Remove one expired operation directory without accepting arbitrary paths."""
        operation_id = uuid.UUID(key)
        operation_root = (self.root / str(operation_id)).resolve()
        if operation_root.parent != self.root:
            raise ValueError("Invalid synchronization operation key")
        if operation_root.exists():
            shutil.rmtree(operation_root)
