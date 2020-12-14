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

__version__      = '0.1.0.dev1'
__author__       = 'John Thorvald Wodder II'
__author_email__ = 'lineinfile@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://github.com/jwodder/lineinfile'

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

from   enum    import Enum
import os
from   pathlib import Path
import re
from   shutil  import copystat
import sys
from   typing  import Any, Optional, TYPE_CHECKING, Union

if sys.version_info[:2] >= (3,9):
    from re import Match, Pattern
    List = list
else:
    from typing import List, Match, Pattern

if TYPE_CHECKING:
    if sys.version_info[:2] >= (3, 8):
        from typing import Protocol
    else:
        from typing_extensions import Protocol

    class Inserter(Protocol):
        def feed(self, i: int, line: str) -> None:
            ...

        def get_index(self) -> Optional[int]:
            ...


Patternish = Union[str, Pattern[str]]

class AtBOF:
    def feed(self, i: int, line: str) -> None:
        pass

    def get_index(self) -> Optional[int]:
        return 0

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return True
        else:
            return NotImplemented


class AtEOF:
    def feed(self, i: int, line: str) -> None:
        pass

    def get_index(self) -> Optional[int]:
        return None

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return True
        else:
            return NotImplemented


class PatternInserter:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern[str] = ensure_compiled(pattern)
        self.i: Optional[int] = None

    def get_index(self) -> Optional[int]:
        return self.i

    def __eq__(self, other: Any) -> bool:
        if type(self) is type(other):
            return (self.pattern, self.i) == (other.pattern, other.i)
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return (
            '{0.__module__}.{0.__name__}(pattern={1.pattern!r}, i={1.i!r})'
            .format(type(self), self)
        )


class AfterFirst(PatternInserter):
    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.pattern.search(line):
            self.i = i+1


class AfterLast(PatternInserter):
    def feed(self, i: int, line: str) -> None:
        if self.pattern.search(line):
            self.i = i+1


class BeforeFirst(PatternInserter):
    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.pattern.search(line):
            self.i = i


class BeforeLast(PatternInserter):
    def feed(self, i: int, line: str) -> None:
        if self.pattern.search(line):
            self.i = i


class MatchFirst:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern[str] = ensure_compiled(pattern)
        self.i: Optional[int] = None
        self.m: Optional[Match[str]] = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None:
            m = self.pattern.search(line)
            if m:
                self.i = i
                self.m = m

    def get_index(self) -> Optional[int]:
        return self.i

    def expand(self, line: str) -> str:
        if self.m is None:
            raise ValueError("No match to expand")  # pragma: no cover
        else:
            return self.m.expand(line)


class MatchLast:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern[str] = ensure_compiled(pattern)
        self.i: Optional[int] = None
        self.m: Optional[Match[str]] = None

    def feed(self, i: int, line: str) -> None:
        m = self.pattern.search(line)
        if m:
            self.i = i
            self.m = m

    def get_index(self) -> Optional[int]:
        return self.i

    def expand(self, line: str) -> str:
        if self.m is None:
            raise ValueError("No match to expand")  # pragma: no cover
        else:
            return self.m.expand(line)


class MatchLineFirst:
    def __init__(self, line: str) -> None:
        self.line: str = chomp(line)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.line == chomp(line):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


class MatchLineLast:
    def __init__(self, line: str) -> None:
        self.line: str = chomp(line)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.line == chomp(line):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


class BackupWhen(Enum):
    CHANGED = "CHANGED"
    ALWAYS = "ALWAYS"

CHANGED = BackupWhen.CHANGED
ALWAYS = BackupWhen.ALWAYS


def add_line_to_string(
    s: str,
    line: str,
    regexp: Optional[Patternish] = None,
    inserter: Optional["Inserter"] = None,
    match_first: bool = False,
    backrefs: bool = False,
) -> str:
    line_matcher: "Inserter"
    if match_first:
        line_matcher = MatchLineFirst(line)
    else:
        line_matcher = MatchLineLast(line)
    rgx: Optional["Inserter"]
    if regexp is None:
        rgx = None
        if backrefs:
            raise ValueError("backrefs=True cannot be given without regexp")
    elif match_first:
        rgx = MatchFirst(regexp)
    else:
        rgx = MatchLast(regexp)
    ins = AtEOF() if inserter is None else inserter
    lines = ascii_splitlines(s)
    for i,ln in enumerate(lines):
        line_matcher.feed(i, ln)
        if rgx is not None:
            rgx.feed(i, ln)
        ins.feed(i, ln)
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
        insert_point = ins.get_index()
        if insert_point is None:
            if lines:
                lines[-1] = ensure_terminated(lines[-1])
            lines.append(ensure_terminated(line))
        else:
            if lines and insert_point == len(lines):
                lines[-1] = ensure_terminated(lines[-1])
            lines.insert(insert_point, ensure_terminated(line))
    return ''.join(lines)

def add_line_to_file(
    filepath: Union[str, os.PathLike],
    line: str,
    regexp: Optional[Patternish] = None,
    inserter: Optional["Inserter"] = None,
    match_first: bool = False,
    backrefs: bool = False,
    backup: Optional[BackupWhen] = None,
    backup_ext: Optional[str] = None,
    create: bool = False,
) -> bool:
    bext = '~' if backup_ext is None else backup_ext
    if backup is not None and not bext:
        raise ValueError("Cannot use empty string as backup_ext")
    p = Path(filepath)
    try:
        before = p.read_text()
    except FileNotFoundError:
        if create:
            before = ''
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
    if (
        not creating and backup is not None
        and (after != before or backup is ALWAYS)
    ):
        bak = p.with_name(p.name + bext)
        bak.write_text(before)
        copystat(p, bak)
    if after != before:
        p.write_text(after)
        return True
    else:
        return False

def remove_lines_from_string(s: str, regexp: Patternish) -> str:
    rgx = ensure_compiled(regexp)
    lines = ascii_splitlines(s)
    lines = [ln for ln in lines if not rgx.search(ln)]
    return ''.join(lines)

def remove_lines_from_file(
    filepath: Union[str, os.PathLike],
    regexp: Patternish,
    backup: Optional[BackupWhen] = None,
    backup_ext: Optional[str] = None,
) -> bool:
    bext = '~' if backup_ext is None else backup_ext
    if backup is not None and not bext:
        raise ValueError("Cannot use empty string as backup_ext")
    p = Path(filepath)
    before = p.read_text()
    after = remove_lines_from_string(before, regexp)
    if backup is not None and (after != before or backup is ALWAYS):
        bak = p.with_name(p.name + bext)
        bak.write_text(before)
        copystat(p, bak)
    if after != before:
        p.write_text(after)
        return True
    else:
        return False

def ensure_compiled(s_or_re: Patternish) -> Pattern[str]:
    if isinstance(s_or_re, str):
        return re.compile(s_or_re)
    else:
        return s_or_re

def ensure_terminated(s: str) -> str:
    if s.endswith(("\r\n", "\n", "\r")):
        return s
    else:
        return s + '\n'

EOL_RGX = re.compile(r'\r\n?|\n')

def ascii_splitlines(s: str) -> List[str]:
    """
    Like `str.splitlines(True)`, except it only treats LF, CR LF, and CR as
    line endings
    """
    lines = []
    lastend = 0
    for m in EOL_RGX.finditer(s):
        lines.append(s[lastend:m.end()])
        lastend = m.end()
    if lastend < len(s):
        lines.append(s[lastend:])
    return lines

def chomp(s: str) -> str:
    """ Remove a LF, CR, or CR LF line ending from a string """
    if s.endswith('\n'):
        s = s[:-1]
    if s.endswith('\r'):
        s = s[:-1]
    return s
