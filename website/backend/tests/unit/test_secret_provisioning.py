"""Generating an installation's secrets so nobody has to invent them.

ELANORA is installed by an institution through a guided setup, not configured
by a platform team with a secret manager. The installation therefore generates
its own secrets once, keeps them, and never rotates them behind the
administrator's back: a changed backup passphrase would make every existing
backup unreadable.
"""

import stat

import pytest
from cryptography.fernet import Fernet

from app.core.secret_provisioning import (
    MANAGED_SECRETS,
    provision_secrets,
    read_env_file,
)


def test_a_fresh_installation_gets_every_secret_it_needs(tmp_path) -> None:
    target = tmp_path / ".env.prod"

    report = provision_secrets(target)

    values = read_env_file(target)
    assert set(report.generated) == set(MANAGED_SECRETS)
    assert report.kept == []
    for name in MANAGED_SECRETS:
        assert values[name], f"{name} must have a value"


def test_running_setup_again_keeps_every_existing_secret(tmp_path) -> None:
    """Re-running the installer must not lock the institution out.

    Rotating the backup passphrase here would silently orphan every backup
    taken so far.
    """
    target = tmp_path / ".env.prod"
    provision_secrets(target)
    before = read_env_file(target)

    report = provision_secrets(target)

    assert report.generated == []
    assert set(report.kept) == set(MANAGED_SECRETS)
    assert read_env_file(target) == before


def test_only_missing_secrets_are_filled_in(tmp_path) -> None:
    target = tmp_path / ".env.prod"
    chosen = "already-chosen-by-the-institution"
    target.write_text(f"JWT_SECRET_KEY={chosen}\n")

    report = provision_secrets(target)

    values = read_env_file(target)
    assert values["JWT_SECRET_KEY"] == chosen
    assert report.kept == ["JWT_SECRET_KEY"]
    assert "ELANORA_BACKUP_PASSPHRASE" in report.generated


def test_settings_that_are_not_secrets_are_left_alone(tmp_path) -> None:
    target = tmp_path / ".env.prod"
    target.write_text("FRONTEND_HOST=https://elanora.example.org\nLOG_LEVEL=INFO\n")

    provision_secrets(target)

    values = read_env_file(target)
    assert values["FRONTEND_HOST"] == "https://elanora.example.org"
    assert values["LOG_LEVEL"] == "INFO"


def test_generated_secrets_are_strong_enough_for_what_reads_them(tmp_path) -> None:
    target = tmp_path / ".env.prod"

    provision_secrets(target)
    values = read_env_file(target)

    # Production configuration refuses a short signing key.
    assert len(values["JWT_SECRET_KEY"]) >= 32
    # The outbox decrypts with Fernet, so this must be a usable key.
    Fernet(values["OUTBOX_ENCRYPTION_KEYS"].encode("ascii"))
    # The recovery procedure requires a substantial passphrase.
    assert len(values["ELANORA_BACKUP_PASSPHRASE"]) >= 16
    assert len(set(values.values())) == len(values), "secrets must differ"


def test_the_file_is_not_readable_by_other_accounts(tmp_path) -> None:
    target = tmp_path / ".env.prod"

    provision_secrets(target)

    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, oct(mode)


def test_the_report_never_contains_a_secret_value(tmp_path) -> None:
    """The installer prints this report; it must be safe to show and log."""
    target = tmp_path / ".env.prod"

    report = provision_secrets(target)

    rendered = repr(report)
    for value in read_env_file(target).values():
        assert value not in rendered


@pytest.mark.parametrize("name", sorted(MANAGED_SECRETS))
def test_every_managed_secret_is_one_the_application_reads(name: str) -> None:
    """A generated secret nothing reads is dead configuration."""
    from app.core.settings import Settings  # noqa: PLC0415

    environment_names = {field.upper() for field in Settings.model_fields}
    assert name in environment_names or name.startswith("ELANORA_")
