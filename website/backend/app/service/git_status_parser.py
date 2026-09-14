"""Git status parsing and analysis service."""

from dataclasses import dataclass
from pathlib import Path

from app.core.centralized_logging import get_logger
from app.schema.common.git import FileStatus

logger = get_logger()

# Constants
MIN_STATUS_LINE_LENGTH = 3


@dataclass
class GitRename:
    """Represents a Git rename operation."""

    old_file: str
    new_file: str
    old_path: Path
    new_path: Path

    def is_eaf_rename(self) -> bool:
        """Check if this is a rename of .eaf files in elan_files directory."""
        return (
            self.old_path.parent == Path("elan_files")
            and self.old_path.suffix.lower() == ".eaf"
            and self.new_path.parent == Path("elan_files")
            and self.new_path.suffix.lower() == ".eaf"
        )


class GitStatusParser:
    """Parses Git status output into structured data."""

    def __init__(self) -> None:
        """Initialize the parser with status mappings."""
        self.status_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "??": "untracked",
        }

    def parse_status_output(self, status_output: str) -> list[dict[str, str]]:
        """Parse git status --porcelain output into structured entries."""
        entries = []

        for line in status_output.strip().split("\n"):
            if not line.strip():
                continue

            # Handle different git status formats
            if (
                line.startswith(" R ")
                or line.startswith("R ")
                or line.startswith("RD ")
                or line.startswith(" RD")
            ):
                # Rename detection: "R  old_file -> new_file" or "RD old_file -> new_file"
                entry = self._parse_rename_line(line)
                if entry:
                    entries.append(entry)
            else:
                # Standard status: "XY filename"
                entry = self._parse_standard_line(line)
                if entry:
                    entries.append(entry)

        return entries

    def _parse_rename_line(self, line: str) -> dict[str, str] | None:
        """Parse a rename line from git status."""
        # Handle different rename prefixes: R, RD
        if line.startswith("RD "):
            content = line[3:].strip()  # Remove 'RD ' prefix
        elif line.startswith(" RD"):
            content = line[3:].strip()  # Remove ' RD' prefix
        elif line.startswith("R "):
            content = line[2:].strip()  # Remove 'R ' prefix
        else:
            content = line[2:].strip()  # Remove ' R' prefix

        if " -> " not in content:
            logger.warning(f"Invalid rename format: {line}")
            return None

        old_file, new_file = content.split(" -> ", 1)
        return {
            "status": "R",
            "filename": content,  # Keep original format for compatibility
            "old_file": old_file.strip(),
            "new_file": new_file.strip(),
        }

    def _parse_standard_line(self, line: str) -> dict[str, str] | None:
        """Parse a standard git status line."""
        if len(line) < MIN_STATUS_LINE_LENGTH:
            return None

        status_code = line[:2].strip()
        filename = (
            line[MIN_STATUS_LINE_LENGTH:] if len(line) > MIN_STATUS_LINE_LENGTH else ""
        )

        return {"status": status_code, "filename": filename}


class GitFileStatusAnalyzer:
    """Analyzes git status and filesystem to determine file states."""

    def __init__(self, parser: GitStatusParser):
        """Initialize with a status parser."""
        self.parser = parser

    def analyze_project_files(
        self, status_output: str, tracked_files: set[str], elan_files_dir: Path
    ) -> tuple[list[FileStatus], set[str]]:
        """Analyze project files and return status list and processed files."""
        entries = self.parser.parse_status_output(status_output)
        files_status = []
        processed_files: set[str] = set()

        # Process git status entries
        for entry in entries:
            file_statuses = self._process_status_entry(entry, processed_files)
            files_status.extend(file_statuses)

        # Check for missing tracked files
        missing_files = self._find_missing_tracked_files(
            tracked_files, processed_files, elan_files_dir
        )
        files_status.extend(missing_files)
        processed_files.update(f.filename for f in missing_files)

        # Check for untracked files
        untracked_files = self._find_untracked_files(
            elan_files_dir, tracked_files, processed_files
        )
        files_status.extend(untracked_files)
        processed_files.update(f.filename for f in untracked_files)

        return files_status, processed_files

    def _process_status_entry(
        self, entry: dict[str, str], processed_files: set[str]
    ) -> list[FileStatus]:
        """Process a single git status entry."""
        status_code = entry["status"]

        if status_code == "R":
            return self._process_rename_entry(entry, processed_files)
        else:
            return self._process_standard_entry(entry, processed_files)

    def _process_rename_entry(
        self, entry: dict[str, str], processed_files: set[str]
    ) -> list[FileStatus]:
        """Process a rename entry into FileStatus objects."""
        old_file = entry["old_file"]
        new_file = entry["new_file"]

        rename = GitRename(
            old_file=old_file,
            new_file=new_file,
            old_path=Path(old_file),
            new_path=Path(new_file),
        )

        if not rename.is_eaf_rename():
            return []

        # Create rename status with metadata
        file_status = FileStatus(
            filename=rename.new_path.as_posix(),
            status="renamed",
            description=f"File renamed from {rename.old_path.as_posix()} to {rename.new_path.as_posix()}",
            old_filename=old_file,
            new_filename=new_file,
        )

        processed_files.add(rename.old_path.as_posix())
        processed_files.add(rename.new_path.as_posix())

        return [file_status]

    def _process_standard_entry(
        self, entry: dict[str, str], processed_files: set[str]
    ) -> list[FileStatus]:
        """Process a standard git status entry."""
        status_code = entry["status"]
        filename = entry["filename"]

        # Map status code to readable status
        status = self.parser.status_map.get(status_code, status_code)
        clean_filename = filename.strip('"').strip("'")
        file_path = Path(clean_filename)

        # Only process .eaf files in elan_files directory
        if (
            file_path.parent == Path("elan_files")
            and file_path.suffix.lower() == ".eaf"
        ):
            file_status = FileStatus(
                filename=file_path.as_posix(),
                status=status,
                description=f"File {file_path.as_posix()} is {status}",
            )
            processed_files.add(file_path.as_posix())
            return [file_status]

        return []

    def _find_missing_tracked_files(
        self, tracked_files: set[str], processed_files: set[str], project_path: Path
    ) -> list[FileStatus]:
        """Find tracked files that are missing from filesystem."""
        missing_files = []

        for tracked_file in tracked_files:
            if (
                tracked_file.startswith("elan_files/")
                and tracked_file.endswith(".eaf")
                and tracked_file not in processed_files
            ):
                file_path = project_path.parent / tracked_file
                if not file_path.exists():
                    missing_files.append(
                        FileStatus(
                            filename=tracked_file,
                            status="deleted",
                            description=f"File {tracked_file} was deleted from filesystem",
                        )
                    )

        return missing_files

    def _find_untracked_files(
        self, elan_files_dir: Path, tracked_files: set[str], processed_files: set[str]
    ) -> list[FileStatus]:
        """Find untracked .eaf files in elan_files directory."""
        untracked_files = []

        for file in elan_files_dir.glob("*.eaf"):
            rel_path = Path("elan_files") / file.name
            rel_path_str = rel_path.as_posix()

            if (
                rel_path_str not in processed_files
                and rel_path_str not in tracked_files
            ):
                untracked_files.append(
                    FileStatus(
                        filename=rel_path_str,
                        status="untracked",
                        description=f"File {rel_path_str} is untracked (not in Git repository)",
                    )
                )

        return untracked_files
