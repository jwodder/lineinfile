"""Tests for the command-line help screens."""

import pytest

from lineinfile.__main__ import main


def get_help_text(capsys: pytest.CaptureFixture, *args: str) -> str:
    with pytest.raises(SystemExit) as excinfo:
        main([*args, "--help"])
    assert excinfo.value.code == 0
    return capsys.readouterr().out


def test_remove_regexp_help_does_not_mention_line(
    capsys: pytest.CaptureFixture,
) -> None:
    """`remove -e` deletes lines; its help must not promise a LINE replacement."""
    help_text = get_help_text(capsys, "remove")
    assert "LINE" not in help_text
    assert "Delete all lines matching REGEX" in help_text


def test_add_regexp_help_mentions_line(capsys: pytest.CaptureFixture) -> None:
    """`add -e` really does replace with LINE; its help is unchanged."""
    help_text = get_help_text(capsys, "add")
    assert "Replace the last line matching REGEX with LINE" in help_text
