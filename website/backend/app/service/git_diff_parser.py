import re
from typing import Any

from app.core.centralized_logging import get_logger

logger = get_logger()
NAME_STATUS_FIELD_COUNT = 2
EXCERPT_LINE_LIMIT = 10
SIMPLE_CONFLICT_LINE_LIMIT = 5


class GitDiffParser:
    """Parses Git diff output into structured data."""

    def __init__(self):
        """Initialize regex patterns for parsing."""
        # Pattern to match diff headers and extract filename/status
        self.diff_header_pattern = re.compile(
            r"^diff --git a/(.*) b/(.*)$", re.MULTILINE
        )
        self.new_file_pattern = re.compile(r"^new file mode \d+$", re.MULTILINE)
        self.deleted_file_pattern = re.compile(r"^deleted file mode \d+$", re.MULTILINE)
        self.index_pattern = re.compile(
            r"^index ([a-f0-9]+)\.\.([a-f0-9]+)", re.MULTILINE
        )
        self.hunk_pattern = re.compile(
            r"^@@\s-(\d+)(?:,(\d+))?\s\+(\d+)(?:,(\d+))?\s@@(.*)$", re.MULTILINE
        )

    def parse_name_status_output(
        self, name_status_output: str
    ) -> tuple[list[str], list[str], list[str]]:
        """Parse git diff --name-status output and return categorized file lists."""
        new_files = []
        modified_files = []
        deleted_files = []

        if not name_status_output.strip():
            return new_files, modified_files, deleted_files

        for line in name_status_output.strip().split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Split by tab (git uses tab as separator)
            parts = stripped_line.split("\t", 1)
            if len(parts) != NAME_STATUS_FIELD_COUNT:
                logger.warning(f"Unexpected git diff --name-status format: {line}")
                continue

            status, filename = parts
            logger.debug(f"Git detected: {status} {filename}")

            if status == "A":
                new_files.append(filename)
            elif status == "M":
                modified_files.append(filename)
            elif status == "D":
                deleted_files.append(filename)
            else:
                logger.warning(f"Unknown git status '{status}' for file: {filename}")

        return new_files, modified_files, deleted_files

    def parse_single_file_diff(self, diff_output: str) -> dict[str, Any]:
        """Parse a single file's git diff output with detailed change information."""
        if not diff_output.strip():
            return {"error": "Empty diff output"}

        # Extract basic file info
        file_info = self._extract_file_info(diff_output)
        if not file_info:
            return {"error": "Could not parse file information"}

        # Determine file status
        status = self._determine_file_status(diff_output, file_info)

        result = {
            "status": status,
            "old_filename": file_info.get("old_filename"),
            "new_filename": file_info.get("new_filename"),
        }

        # Add detailed information based on status
        if status == "M":
            modification_details = self._extract_detailed_modifications(
                diff_output, file_info["filename"]
            )
            result.update(modification_details)

        return result

    def _extract_file_info(self, diff_output: str) -> dict[str, str]:
        """Extract filename(s) from diff header."""
        header_match = self.diff_header_pattern.search(diff_output)
        if not header_match:
            return None

        old_file = header_match.group(1)
        new_file = header_match.group(2)

        return {
            "old_filename": old_file,
            "new_filename": new_file,
            "filename": new_file if new_file != "/dev/null" else old_file,
        }

    def _determine_file_status(
        self, diff_output: str, file_info: dict[str, str]
    ) -> str:
        """Determine if file is Added, Modified, or Deleted."""
        # Check for new file
        if self.new_file_pattern.search(diff_output):
            return "A"
        # Check for deleted file
        if self.deleted_file_pattern.search(diff_output):
            return "D"
        # Check if old or new filename is /dev/null
        if file_info["old_filename"] == "/dev/null":
            return "A"
        elif file_info["new_filename"] == "/dev/null":
            return "D"
        # Otherwise it's a modification
        return "M"

    def _extract_detailed_modifications(
        self, diff_output: str, filename: str
    ) -> dict[str, Any]:
        """Extract comprehensive modification details for changed files."""
        lines = diff_output.split("\n")

        modifications = {
            "total_additions": 0,
            "total_deletions": 0,
            "hunks": [],
            "change_summary": "",
            "file_stats": {},
        }

        current_hunk = None
        old_line_num = 0
        new_line_num = 0
        context_before = []

        for line in lines:
            # Parse hunk headers
            hunk_match = self.hunk_pattern.match(line)
            if hunk_match:
                # Save previous hunk
                if current_hunk:
                    modifications["hunks"].append(current_hunk)

                old_start = int(hunk_match.group(1))
                new_start = int(hunk_match.group(3))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

                old_line_num = old_start
                new_line_num = new_start

                current_hunk = {
                    "hunk_header": line,
                    "old_start": old_start,
                    "old_count": old_count,
                    "new_start": new_start,
                    "new_count": new_count,
                    "context": hunk_match.group(5).strip()
                    if hunk_match.group(5)
                    else "",
                    "changes": [],  # This contains ALL the detail
                    "additions": 0,
                    "deletions": 0,
                }
                context_before = []
                continue

            # Process change lines
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                modifications["total_additions"] += 1
                if current_hunk:
                    current_hunk["additions"] += 1

                change_detail = {
                    "type": "addition",
                    "line_number": new_line_num,
                    "content": content,
                    "context_before": context_before.copy() if context_before else [],
                }

                if current_hunk:
                    current_hunk["changes"].append(change_detail)

                new_line_num += 1
                context_before = []

            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:]
                modifications["total_deletions"] += 1
                if current_hunk:
                    current_hunk["deletions"] += 1

                change_detail = {
                    "type": "deletion",
                    "line_number": old_line_num,
                    "content": content,
                    "context_before": context_before.copy() if context_before else [],
                }

                if current_hunk:
                    current_hunk["changes"].append(change_detail)

                old_line_num += 1
                context_before = []

            elif line.startswith(" "):
                # Context line
                content = line[1:]
                if current_hunk:
                    current_hunk["changes"].append(
                        {
                            "type": "context",
                            "content": content,
                            "old_line_number": old_line_num,
                            "new_line_number": new_line_num,
                        }
                    )

                # Track context for next additions/deletions
                context_before.append(content.strip())

                old_line_num += 1
                new_line_num += 1

        # Add final hunk
        if current_hunk:
            modifications["hunks"].append(current_hunk)

        # Create concise summary
        modifications["change_summary"] = self._create_modification_summary(
            modifications
        )
        modifications["file_stats"] = self._create_file_stats(modifications)

        return modifications

    def _create_modification_summary(self, modifications: dict) -> str:
        """Create a concise summary of modifications."""
        hunks_count = len(modifications["hunks"])

        if hunks_count == 1:
            return f"+{modifications['total_additions']} -{modifications['total_deletions']} lines in 1 section"
        else:
            return f"+{modifications['total_additions']} -{modifications['total_deletions']} lines in {hunks_count} sections"

    def _create_file_stats(self, modifications: dict) -> dict:
        """Create essential file statistics."""
        return {
            "total_hunks": len(modifications["hunks"]),
            "net_line_change": modifications["total_additions"]
            - modifications["total_deletions"],
        }

    def convert_to_conflict_format(self, diff_data: dict, branch_info: dict) -> dict:
        """Convert existing diff format to conflict resolution format."""
        conflict_sections = []

        for i, hunk in enumerate(diff_data.get("hunks", [])):
            # Group additions and deletions into conflict-like sections
            removed_lines = [
                change["content"]
                for change in hunk["changes"]
                if change["type"] == "deletion"
            ]
            added_lines = [
                change["content"]
                for change in hunk["changes"]
                if change["type"] == "addition"
            ]

            conflict_section = {
                "section_id": i,
                "line_range": {
                    "start": hunk["old_start"],
                    "end": hunk["old_start"] + hunk["old_count"],
                },
                # Convert to expected format
                "current_excerpt": {
                    "content": "\n".join(removed_lines[:EXCERPT_LINE_LIMIT]),
                    "is_truncated": len(removed_lines) > EXCERPT_LINE_LIMIT,
                    "total_lines": len(removed_lines),
                    "total_chars": sum(len(line) for line in removed_lines),
                },
                "incoming_excerpt": {
                    "content": "\n".join(added_lines[:EXCERPT_LINE_LIMIT]),
                    "is_truncated": len(added_lines) > EXCERPT_LINE_LIMIT,
                    "total_lines": len(added_lines),
                    "total_chars": sum(len(line) for line in added_lines),
                },
                "base_excerpt": None,
                "content_stats": {
                    "current_lines": len(removed_lines),
                    "incoming_lines": len(added_lines),
                    "base_lines": 0,
                    "current_chars": sum(len(line) for line in removed_lines),
                    "incoming_chars": sum(len(line) for line in added_lines),
                },
                "conflict_type": self._classify_hunk_type(removed_lines, added_lines),
                "complexity": "simple"
                if len(removed_lines) + len(added_lines) <= SIMPLE_CONFLICT_LINE_LIMIT
                else "moderate",
                "auto_resolvable": True,
                "suggested_resolution": self._suggest_hunk_resolution(
                    removed_lines, added_lines
                ),
                "context_info": {
                    "has_before_context": True,
                    "has_after_context": True,
                    "context_lines_before": 3,
                    "context_lines_after": 3,
                },
            }

            conflict_sections.append(conflict_section)

        return {
            "conflict_metadata": {
                "current_branch": branch_info.get("current_branch", "master"),
                "incoming_branch": branch_info.get("incoming_branch", "unknown"),
                "total_conflicts": len(conflict_sections),
                "file_type": "eaf",
                "file_stats": {
                    "total_lines": diff_data.get("total_additions", 0)
                    + diff_data.get("total_deletions", 0),
                    "conflict_lines": sum(
                        s["content_stats"]["current_lines"]
                        + s["content_stats"]["incoming_lines"]
                        for s in conflict_sections
                    ),
                },
            },
            "merge_data": {
                "conflict_sections": conflict_sections,
                "has_conflicts": len(conflict_sections) > 0,
                "is_resolvable": True,
                "resolution_strategies": [
                    "accept_current",
                    "accept_incoming",
                    "manual",
                    "section_by_section",
                ],
            },
            "resolution_options": {
                "can_auto_resolve": True,
                "has_binary_conflict": False,
                "preview_available": len(conflict_sections) > 0,
                "suggested_strategy": "section_by_section"
                if len(conflict_sections) > 1
                else "auto_resolve",
            },
            # Keep your original data
            "original_diff_data": diff_data,
        }

    def _classify_hunk_type(self, removed_lines: list, added_lines: list) -> str:
        """Classify the type of change."""
        if not removed_lines and added_lines:
            return "addition"
        elif removed_lines and not added_lines:
            return "deletion"
        elif len(removed_lines) == 1 and len(added_lines) == 1:
            return "single_line_change"
        else:
            return "multi_line_change"

    def _suggest_hunk_resolution(self, removed_lines: list, added_lines: list) -> str:
        """Suggest resolution for this hunk."""
        if not removed_lines:
            return "incoming"  # Pure addition
        elif not added_lines:
            return "current"  # Pure deletion
        else:
            return "manual"  # Modification
