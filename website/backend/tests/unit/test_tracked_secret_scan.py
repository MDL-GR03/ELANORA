"""Tests for the dependency-free tracked credential scanner."""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[2] / "scripts/check_tracked_secrets.py"
SPEC = importlib.util.spec_from_file_location("check_tracked_secrets", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
scanner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scanner
SPEC.loader.exec_module(scanner)


def test_scanner_detects_credentials_without_echoing_values() -> None:
    secret = "AKIA" + "IOSFODNN7EXAMPLE"

    findings = scanner.scan_content("settings.py", f'KEY = "{secret}"')

    assert findings == ["settings.py:1: possible AWS access key"]
    assert secret not in repr(findings)


def test_scanner_ignores_documented_placeholders() -> None:
    content = "API_KEY=replace-me\nPASSWORD=development-only\n"

    assert scanner.scan_content(".env.example", content) == []


def test_scanner_detects_private_key_headers() -> None:
    header = "-----BEGIN " + "PRIVATE KEY-----"
    findings = scanner.scan_content("deployment.pem", f"{header}\nredacted")

    assert findings == ["deployment.pem:1: possible private key"]
