from __future__ import annotations
import pytest
from lineinfile import ascii_splitlines, chomp, ensure_terminated, unescape


@pytest.mark.parametrize(
    "s,lines",
    [
        ("", []),
        ("foobar", ["foobar"]),
        ("foo\n", ["foo\n"]),
        ("foo\r", ["foo\r"]),
        ("foo\r\n", ["foo\r\n"]),
        ("foo\n\r", ["foo\n", "\r"]),
        ("foo\nbar", ["foo\n", "bar"]),
        ("foo\rbar", ["foo\r", "bar"]),
        ("foo\r\nbar", ["foo\r\n", "bar"]),
        ("foo\n\rbar", ["foo\n", "\r", "bar"]),
        ("foo\n\nbar", ["foo\n", "\n", "bar"]),
        ("foo\n\nbar\n", ["foo\n", "\n", "bar\n"]),
        (
            "Why\vare\fthere\x1cso\x1ddang\x1emany\x85line\u2028separator\u2029"
            "characters?",
            [
                "Why\vare\fthere\x1cso\x1ddang\x1emany\x85line\u2028separator\u2029"
                "characters?"
            ],
        ),
    ],
)
def test_ascii_splitlines(s: str, lines: list[str]) -> None:
    assert ascii_splitlines(s) == lines


@pytest.mark.parametrize(
    "s,chomped",
    [
        ("foobar", "foobar"),
        ("foobar\n", "foobar"),
        ("foobar\r\n", "foobar"),
        ("foobar\r", "foobar"),
        ("foobar\n\r", "foobar\n"),
        ("foobar\n\n", "foobar\n"),
        ("foobar\nbaz", "foobar\nbaz"),
    ],
)
def test_chomp(s: str, chomped: str) -> None:
    assert chomp(s) == chomped


@pytest.mark.parametrize(
    "s,terminated",
    [
        ("foobar", "foobar\n"),
        ("foobar\n", "foobar\n"),
        ("foobar\r", "foobar\r"),
        ("foobar\r\n", "foobar\r\n"),
        ("foobar\n\r", "foobar\n\r"),
        ("foo\nbar", "foo\nbar\n"),
    ],
)
def test_ensure_terminated(s: str, terminated: str) -> None:
    assert ensure_terminated(s) == terminated


@pytest.mark.parametrize(
    "src,dest",
    [
        ("foo", "foo"),
        (r"foo\n", "foo\n"),
        (r"foo\\n", "foo\\n"),
        (r"foo\\\n", "foo\\\n"),
        (r"foo\012", "foo\n"),
        (r"foo\x0A", "foo\n"),
        (r"foo\u000A", "foo\n"),
        (r"foo\\bar", r"foo\bar"),
        (r"foo\'bar", "foo'bar"),
        (r"foo\"bar", 'foo"bar'),
        (r"foo\abar", "foo\abar"),
        (r"foo\bbar", "foo\bbar"),
        (r"foo\fbar", "foo\fbar"),
        (r"foo\rbar", "foo\rbar"),
        (r"foo\tbar", "foo\tbar"),
        (r"foo\vbar", "foo\vbar"),
        (r"\U0001F410", "\U0001f410"),
        ("åéîøü", "åéîøü"),
        (r"\u2603", "\u2603"),
        ("\u2603", "\u2603"),
        ("\U0001f410", "\U0001f410"),
        (r"\N{SNOWMAN}", "\u2603"),
    ],
)
def test_unescape(src: str, dest: str) -> None:
    assert unescape(src) == dest
