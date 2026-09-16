"""Where the first administrator's password comes from during setup.

Guided setup runs without a terminal, so the password has to arrive on
standard input. Typing it at a prompt stays the default for someone running
the command by hand, and neither path may accept an empty password or one the
person did not confirm.
"""

import io

import pytest

from app.cli.bootstrap import read_password


def test_a_person_at_a_terminal_types_it_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    entered = iter(["chosen-by-the-administrator", "chosen-by-the-administrator"])
    monkeypatch.setattr("app.cli.bootstrap.getpass.getpass", lambda _: next(entered))

    assert read_password(from_stdin=False) == "chosen-by-the-administrator"


def test_a_mistyped_confirmation_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    entered = iter(["first-attempt-value", "second-attempt-value"])
    monkeypatch.setattr("app.cli.bootstrap.getpass.getpass", lambda _: next(entered))

    with pytest.raises(ValueError, match="confirmation does not match"):
        read_password(from_stdin=False)


def test_guided_setup_passes_it_on_standard_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("generated-by-the-installer\n"))

    assert read_password(from_stdin=True) == "generated-by-the-installer"


def test_an_empty_password_is_refused_however_it_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))

    with pytest.raises(ValueError, match="password"):
        read_password(from_stdin=True)
