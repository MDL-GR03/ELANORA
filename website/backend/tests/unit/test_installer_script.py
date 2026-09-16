"""The guided installation, exercised without touching real Docker.

An installer nobody has run is the thing that fails on the day an institution
first tries it. These tests run the real script against a stand-in `docker`
that records what it was asked to do, so the questions it asks, the
configuration it writes and the commands it issues are all checked.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[4]
INSTALLER = REPOSITORY_ROOT / "installer" / "install.sh"
SHELL = shutil.which("sh") or "/bin/sh"

# Stands in for Docker: records every call, and answers the two questions the
# installer asks a running container (how many institutions exist, and a
# generated password).
FAKE_DOCKER = """#!/usr/bin/env sh
printf '%s\\n' "$*" >> "$FAKE_DOCKER_LOG"
case "$*" in
  *"select(func.count()).select_from(Instance)"*) echo "$FAKE_INSTITUTION_COUNT" ;;
  *"secrets.token_urlsafe"*) echo "generated-admin-password" ;;
  *setup_installation*) echo '{"generated": [], "kept": []}' ;;
esac
exit 0
"""


@pytest.fixture
def installation(tmp_path: Path) -> dict[str, Path]:
    """A repository tree holding just what the installer touches."""
    root = tmp_path / "elanora"
    (root / "installer").mkdir(parents=True)
    (root / "website" / "docker" / "website-prod").mkdir(parents=True)
    (root / "website" / "env").mkdir(parents=True)
    shutil.copy(INSTALLER, root / "installer" / "install.sh")
    (root / "website" / "docker" / "website-prod" / "docker-compose.yml").write_text(
        "services: {}\n"
    )
    (root / "website" / "env" / ".env.prod.example").write_text(
        "ENVIRONMENT=dev\nFRONTEND_HOST=http://localhost:3000\nLOG_LEVEL=INFO\n"
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    docker = binaries / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    return {"root": root, "bin": binaries, "log": tmp_path / "docker.log"}


def _run(installation: dict[str, Path], *arguments: str) -> subprocess.CompletedProcess:
    environment = os.environ | {
        "PATH": f"{installation['bin']}:{os.environ['PATH']}",
        "FAKE_DOCKER_LOG": str(installation["log"]),
        "FAKE_INSTITUTION_COUNT": "0",
    }
    return subprocess.run(  # noqa: S603 - the script under test
        [SHELL, str(installation["root"] / "installer" / "install.sh"), *arguments],
        capture_output=True,
        text=True,
        env=environment,
        stdin=subprocess.DEVNULL,
        check=False,
    )


ANSWERS = (
    "--url",
    "https://elanora.example.org",
    "--institution",
    "Example Institute",
    "--admin-email",
    "admin@example.org",
    "--admin-first-name",
    "Ada",
    "--admin-last-name",
    "Researcher",
)


def _env_values(installation: dict[str, Path]) -> dict[str, str]:
    text = (installation["root"] / "website" / "env" / ".env.prod").read_text()
    return dict(
        line.split("=", 1)
        for line in text.splitlines()
        if line.strip() and not line.startswith("#") and "=" in line
    )


def test_a_complete_installation_configures_starts_and_bootstraps(
    installation: dict[str, Path],
) -> None:
    result = _run(installation, *ANSWERS)

    assert result.returncode == 0, result.stderr
    calls = installation["log"].read_text()
    assert "setup_installation" in calls, "secrets must be generated"
    assert "up --build --wait" in calls, "the installation must be started"
    assert "app.cli.bootstrap" in calls, "the institution must be created"
    assert "--password-stdin" in calls, "setup has no terminal to prompt at"
    assert "generated-admin-password" in result.stdout, "the admin must be told it"


def test_it_asks_only_what_the_institution_alone_can_decide(
    installation: dict[str, Path],
) -> None:
    """Every secret is generated, so none of them is ever an answer."""
    result = _run(installation, *ANSWERS)

    values = _env_values(installation)
    assert values["FRONTEND_HOST"] == "https://elanora.example.org"
    assert values["VITE_API_URL"] == "https://elanora.example.org/api/v1"
    assert values["ENVIRONMENT"] == "prod"
    assert values["LOG_LEVEL"] == "INFO", "unrelated settings are left alone"
    assert "password" not in result.stdout.lower().split("sign in")[0]


def test_the_hostname_is_derived_rather_than_asked_for_twice(
    installation: dict[str, Path],
) -> None:
    _run(installation, *ANSWERS)

    # The institution's domain is read from the URL it already gave.
    assert "--domain elanora.example.org" in installation["log"].read_text()


def test_running_it_again_keeps_the_institution_that_exists(
    installation: dict[str, Path],
) -> None:
    _run(installation, *ANSWERS)
    installation["log"].write_text("")
    environment_before = _env_values(installation)

    environment = os.environ | {
        "PATH": f"{installation['bin']}:{os.environ['PATH']}",
        "FAKE_DOCKER_LOG": str(installation["log"]),
        "FAKE_INSTITUTION_COUNT": "1",
    }
    result = subprocess.run(  # noqa: S603 - the script under test
        [SHELL, str(installation["root"] / "installer" / "install.sh"), *ANSWERS],
        capture_output=True,
        text=True,
        env=environment,
        stdin=subprocess.DEVNULL,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "app.cli.bootstrap" not in installation["log"].read_text()
    assert "already exists" in result.stdout
    assert _env_values(installation) == environment_before


def test_the_configuration_file_is_not_readable_by_other_accounts(
    installation: dict[str, Path],
) -> None:
    _run(installation, *ANSWERS)

    target = installation["root"] / "website" / "env" / ".env.prod"
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, oct(mode)


def test_setup_without_a_terminal_says_what_is_missing(
    installation: dict[str, Path],
) -> None:
    """Guided setup passes options; a missing one must not hang forever."""
    result = _run(installation, "--url", "https://elanora.example.org")

    assert result.returncode != 0
    assert "must be given with a command-line option" in result.stderr


def test_a_host_without_docker_is_told_plainly(installation: dict[str, Path]) -> None:
    result = subprocess.run(  # noqa: S603 - the script under test
        [SHELL, str(installation["root"] / "installer" / "install.sh"), "--check"],
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent", "HOME": os.environ.get("HOME", "")},
        check=False,
    )

    assert result.returncode != 0
    assert "docker" in result.stderr.lower()
