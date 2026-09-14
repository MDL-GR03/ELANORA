#!/usr/bin/env python3
"""Reject tracked files that contain recognizable credential material."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SecretPattern:
    name: str
    expression: re.Pattern[str]


PATTERNS = (
    SecretPattern(
        "private key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    SecretPattern("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    SecretPattern(
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    SecretPattern("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    SecretPattern(
        "OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")
    ),
    SecretPattern("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    SecretPattern(
        "Stripe live key", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b")
    ),
    SecretPattern(
        "SendGrid API key",
        re.compile(r"\bSG\.[0-9A-Za-z_-]{16,}\.[0-9A-Za-z_-]{16,}\b"),
    ),
)


def scan_content(path: str, content: str) -> list[str]:
    """Return safe finding descriptions without reproducing matched values."""
    findings: list[str] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        for pattern in PATTERNS:
            if pattern.expression.search(line):
                findings.append(f"{path}:{line_number}: possible {pattern.name}")
    return findings


def _tracked_files() -> list[Path]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required to scan tracked files")
    result = subprocess.run(  # noqa: S603 - fixed Git arguments, no shell
        [git, "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        REPOSITORY_ROOT / item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0")
        if item
    ]


def _unsafe_tracked_name(path: Path) -> str | None:
    relative = path.relative_to(REPOSITORY_ROOT)
    name = path.name.casefold()
    if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
        return f"{relative}: tracked environment file"
    if path.suffix.casefold() in {".key", ".p12", ".pfx"}:
        return f"{relative}: tracked private credential file"
    return None


def main() -> int:
    """Scan tracked, reasonably sized text files and return a CI-friendly status."""
    findings: list[str] = []
    for path in _tracked_files():
        unsafe_name = _unsafe_tracked_name(path)
        if unsafe_name:
            findings.append(unsafe_name)
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if len(raw) > MAX_TEXT_FILE_BYTES or b"\0" in raw:
            continue
        findings.extend(
            scan_content(
                str(path.relative_to(REPOSITORY_ROOT)),
                raw.decode("utf-8", errors="replace"),
            )
        )

    if findings:
        print("Tracked credential scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        print(
            "Matched credential values were intentionally not printed.", file=sys.stderr
        )
        return 1
    print("Tracked credential scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
