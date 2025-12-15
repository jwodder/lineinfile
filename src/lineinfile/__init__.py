"""
Add & remove lines in files by regex

Inspired by (but not affiliated with) `the Ansible module of the same name`__,
``lineinfile`` provides a command and library for adding a line to a file if
it's not already there and for removing lines matching a pattern from a file.
There are options for using a regex to find a line to update or to determine
which line to insert before or after.  There are options for backing up the
modified file with a custom file extension and for treating a nonexistent file
as though it's just empty.  There's even an option for determining the line to
insert based on capturing groups in the matching regex.

__ https://docs.ansible.com/ansible/latest/collections/ansible/builtin/
   lineinfile_module.html

Unlike the Ansible module, this package does not perform any management of file
attributes; those must be set externally.

Visit <https://github.com/jwodder/lineinfile> for more information.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import os
from pathlib import Path
import re
from re import Pattern
from shutil import copystat
from typing import Any, TypeAlias

__version__ = "0.5.0"
__author__ = "John Thorvald Wodder II"
__author_email__ = "lineinfile@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/lineinfile"

__all__ = [
    "ALWAYS",
    "AfterFirst",
    "AfterLast",
    "AtBOF",
    "AtEOF",
    "BackupWhen",
    "BeforeFirst",
    "BeforeLast",
    "CHANGED",
    "add_line_to_file",
    "add_line_to_string",
    "remove_lines_from_file",
    "remove_lines_from_string",
]

Patternish: TypeAlias = str | Pattern[str]


class Inserter(ABC):
    @abstractmethod
    def update_state(self, state: int | None, lineno: int, line: str) -> int | None: ...

    def get_feeder(self) -> LineFeeder:
        return LineFeeder(self)


class LineFeeder:
    def __init__(self, inserter: Inserter):
        self.inserter = inserter
        self.state: int | None = None

    def feed(self, lineno: int, line: str) -> None:
        self.state = self.inserter.update_state(self.state, lineno, line)

    def get_index(self) -> int | None:
        return self.state


class AtBOF(Inserter):
    """Inserter that always inserts at the beginning of the file"""

    def update_state(self, _state: int | None, _lineno: int, _line: str) -> int | None:
        return 0

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return True
        else:
            return NotImplemented


class AtEOF(Inserter):
    """Inserter that always inserts at the end of the file"""

    def update_state(self, _state: int | None, _lineno: int, _line: str) -> int | None:
        return None

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return True
        else:
            return NotImplemented


class PatternInserter(Inserter):
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: re.Pattern[str] = re.compile(pattern)

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return bool(self.pattern == other.pattern)
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return "{0.__module__}.{0.__name__}(pattern={1.pattern!r})".format(
            type(self), self
        )


class AfterFirst(PatternInserter):
    """
    Inserter that inserts after the first input line that matches the given
    regular expression (either a string or a compiled pattern object), or at
    the end of the file if no line matches
    """

    def update_state(self, state: int | None, lineno: int, line: str) -> int | None:
        if state is None and self.pattern.search(line):
            return lineno + 1
        else:
            return state


class AfterLast(PatternInserter):
    """
    Inserter that inserts after the last input line that matches the given
    regular expression (either a string or a compiled pattern object), or at
    the end of the file if no line matches
    """

    def update_state(self, state: int | None, lineno: int, line: str) -> int | None:
        if self.pattern.search(line):
            return lineno + 1
        else:
            return state


class BeforeFirst(PatternInserter):
    """
    Inserter that inserts before the first input line that matches the given
    regular expression (either a string or a compiled pattern object), or at
    the end of the file if no line matches
    """

    def update_state(self, state: int | None, lineno: int, line: str) -> int | None:
        if state is None and self.pattern.search(line):
            return lineno
        else:
            return state


class BeforeLast(PatternInserter):
    """
    Inserter that inserts before the last input line that matches the given
    regular expression (either a string or a compiled pattern object), or at
    the end of the file if no line matches
    """

    def update_state(self, state: int | None, lineno: int, line: str) -> int | None:
        if self.pattern.search(line):
            return lineno
        else:
            return state


class Matcher(ABC):
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: re.Pattern[str] = re.compile(pattern)
        self.i: int | None = None
        self.m: re.Match[str] | None = None

    @abstractmethod
    def feed(self, i: int, line: str) -> None: ...

    def get_index(self) -> int | None:
        return self.i

    def expand(self, line: str) -> str:
        if self.m is None:
            raise ValueError("No match to expand")  # pragma: no cover
        else:
            return self.m.expand(line)


class MatchFirst(Matcher):
    def feed(self, i: int, line: str) -> None:
        if self.i is None:
            m = self.pattern.search(line)
            if m:
                self.i = i
                self.m = m


class MatchLast(Matcher):
    def feed(self, i: int, line: str) -> None:
        m = self.pattern.search(line)
        if m:
            self.i = i
            self.m = m


class ExactMatchFirst:
    def __init__(self, line: str) -> None:
        self.line: str = chomp(line)
        self.i: int | None = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.line == chomp(line):
            self.i = i

    def get_index(self) -> int | None:
        return self.i


class ExactMatchLast:
    def __init__(self, line: str) -> None:
        self.line: str = chomp(line)
        self.i: int | None = None

    def feed(self, i: int, line: str) -> None:
        if self.line == chomp(line):
            self.i = i

    def get_index(self) -> int | None:
        return self.i


class BackupWhen(Enum):
    CHANGED = "CHANGED"
    ALWAYS = "ALWAYS"


CHANGED = BackupWhen.CHANGED
ALWAYS = BackupWhen.ALWAYS


def add_line_to_string(
    s: str,
    line: str,
    regexp: Patternish | None = None,
    inserter: Inserter | None = None,
    match_first: bool = False,
    backrefs: bool = False,
) -> str:
    """
    Add the given ``line`` to the string ``s`` if it is not already present and
    return the result.  If ``regexp`` is set to a regular expression (either a
    string or a compiled pattern object) and it matches any lines in the input,
    ``line`` will replace the last matching line (or the first matching line,
    if ``match_first=True``).  If the regular expression does not match any
    lines (or no regular expression is specified) and ``line`` is not found in
    the input, the line is inserted at the end of the input by default; this
    can be changed by passing the appropriate object as the ``inserter``
    argument; see "Inserters_" below.

    When ``backrefs`` is true, if ``regexp`` matches, the capturing groups in
    the regular expression are used to expand any ``\\n``, ``\\g<n>``, or
    ``\\g<name>`` backreferences in ``line``, and the resulting string replaces
    the matched line in the input.  If ``backrefs`` is true and ``regexp`` does
    not match, the input is left unchanged.  It is an error to set ``backrefs``
    to true without also setting ``regexp``.
    """
    line_matcher: ExactMatchFirst | ExactMatchLast
    if match_first:
        line_matcher = ExactMatchFirst(line)
    else:
        line_matcher = ExactMatchLast(line)
    rgx: Matcher | None
    if regexp is None:
        rgx = None
        if backrefs:
            raise ValueError("backrefs=True cannot be given without regexp")
    elif match_first:
        rgx = MatchFirst(regexp)
    else:
        rgx = MatchLast(regexp)
    insfeeder = (AtEOF() if inserter is None else inserter).get_feeder()
    lines = ascii_splitlines(s)
    for i, ln in enumerate(lines):
        line_matcher.feed(i, ln)
        if rgx is not None:
            rgx.feed(i, ln)
        insfeeder.feed(i, ln)
    match_point = None if rgx is None else rgx.get_index()
    if match_point is None:
        if backrefs:
            return s
        match_point = line_matcher.get_index()
    if match_point is not None:
        assert match_point < len(lines)
        if backrefs:
            assert rgx is not None and rgx.get_index() is not None
            line = rgx.expand(line)
        lines[match_point] = ensure_terminated(line)
    else:
        insert_point = insfeeder.get_index()
        if insert_point is None:
            if lines:
                lines[-1] = ensure_terminated(lines[-1])
            lines.append(ensure_terminated(line))
        else:
            if lines and insert_point == len(lines):
                lines[-1] = ensure_terminated(lines[-1])
            lines.insert(insert_point, ensure_terminated(line))
    return "".join(lines)


def add_line_to_file(
    filepath: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    line: str,
    regexp: Patternish | None = None,
    inserter: Inserter | None = None,
    match_first: bool = False,
    backrefs: bool = False,
    backup: BackupWhen | None = None,
    backup_ext: str | None = None,
    create: bool = False,
    encoding: str | None = None,
    errors: str | None = None,
) -> bool:
    """
    Add the given ``line`` to the file at ``filepath`` if it is not already
    present.  Returns ``True`` if the file is modified.  If ``regexp`` is set
    to a regular expression (either a string or a compiled pattern object) and
    it matches any lines in the file, ``line`` will replace the last matching
    line (or the first matching line, if ``match_first=True``).  If the regular
    expression does not match any lines (or no regular expression is specified)
    and ``line`` is not found in the file, the line is inserted at the end of
    the file by default; this can be changed by passing the appropriate object
    as the ``inserter`` argument; see "Inserters_" below.

    When ``backrefs`` is true, if ``regexp`` matches, the capturing groups in
    the regular expression are used to expand any ``\\n``, ``\\g<n>``, or
    ``\\g<name>`` backreferences in ``line``, and the resulting string replaces
    the matched line in the input.  If ``backrefs`` is true and ``regexp`` does
    not match, the file is left unchanged.  It is an error to set ``backrefs``
    to true without also setting ``regexp``.

    When ``backup`` is set to ``lineinfile.CHANGED``, a backup of the file's
    original contents is created if the file is modified.  When ``backup`` is
    set to ``lineinfile.ALWAYS``, a backup is always created, regardless of
    whether the file is modified.  The name of the backup file will be the same
    as the original, with the value of ``backup_ext`` (default: ``~``)
    appended.

    If ``create`` is true and ``filepath`` does not exist, pretend it's empty
    instead of erroring, and create it with the results of the operation.  No
    backup file will ever be created for a nonexistent file.  If ``filepath``
    does not exist and no changes are made (because ``backrefs`` was set and
    ``regexp`` didn't match), the file will not be created.
    """
    bext = "~" if backup_ext is None else backup_ext
    if backup is not None and not bext:
        raise ValueError("Cannot use empty string as backup_ext")
    p = Path(os.fsdecode(filepath))
    try:
        before = p.read_text(encoding=encoding, errors=errors)
    except FileNotFoundError:
        if create:
            before = ""
            creating = True
        else:
            raise
    else:
        creating = False
    after = add_line_to_string(
        before,
        line,
        regexp=regexp,
        inserter=inserter,
        match_first=match_first,
        backrefs=backrefs,
    )
    if not creating and backup is not None and (after != before or backup is ALWAYS):
        bak = p.with_name(p.name + bext)
        bak.write_text(before, encoding=encoding, errors=errors)
        copystat(p, bak)
    if after != before:
        p.write_text(after, encoding=encoding, errors=errors)
        return True
    else:
        return False


def remove_lines_from_string(s: str, regexp: Patternish) -> str:
    """
    Delete all lines from the string ``s`` that match the regular expression
    ``regexp`` (either a string or a compiled pattern object) and return the
    result.
    """
    lines = ascii_splitlines(s)
    lines = [ln for ln in lines if not re.search(regexp, ln)]
    return "".join(lines)


def remove_lines_from_file(
    filepath: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    regexp: Patternish,
    backup: BackupWhen | None = None,
    backup_ext: str | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> bool:
    """
    Delete all lines from the file at ``filepath`` that match the regular
    expression ``regexp`` (either a string or a compiled pattern object).
    Returns ``True`` if the file is modified.

    When ``backup`` is set to ``lineinfile.CHANGED``, a backup of the file's
    original contents is created if the file is modified.  When ``backup`` is
    set to ``lineinfile.ALWAYS``, a backup is always created, regardless of
    whether the file is modified.  The name of the backup file will be the same
    as the original, with the value of ``backup_ext`` (default: ``~``)
    appended.
    """
    bext = "~" if backup_ext is None else backup_ext
    if backup is not None and not bext:
        raise ValueError("Cannot use empty string as backup_ext")
    p = Path(os.fsdecode(filepath))
    before = p.read_text(encoding=encoding, errors=errors)
    after = remove_lines_from_string(before, regexp)
    if backup is not None and (after != before or backup is ALWAYS):
        bak = p.with_name(p.name + bext)
        bak.write_text(before, encoding=encoding, errors=errors)
        copystat(p, bak)
    if after != before:
        p.write_text(after, encoding=encoding, errors=errors)
        return True
    else:
        return False


def ensure_terminated(s: str) -> str:
    if s.endswith(("\r\n", "\n", "\r")):
        return s
    else:
        return s + "\n"


EOL_RGX = re.compile(r"\r\n?|\n")


def ascii_splitlines(s: str) -> list[str]:
    """
    Like `str.splitlines(True)`, except it only treats LF, CR LF, and CR as
    line endings
    """
    lines = []
    lastend = 0
    for m in EOL_RGX.finditer(s):
        lines.append(s[lastend : m.end()])
        lastend = m.end()
    if lastend < len(s):
        lines.append(s[lastend:])
    return lines


def chomp(s: str) -> str:
    """Remove a LF, CR, or CR LF line ending from a string"""
    if s.endswith("\n"):
        s = s[:-1]
    if s.endswith("\r"):
        s = s[:-1]
    return s


def unescape(s: str) -> str:
    # <https://stackoverflow.com/a/57192592/744178>
    return s.encode("latin-1", "backslashreplace").decode("unicode_escape")
