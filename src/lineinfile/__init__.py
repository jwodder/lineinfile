"""
Add & remove lines in files by regex

Visit <https://github.com/jwodder/lineinfile> for more information.
"""

__version__      = '0.1.0.dev1'
__author__       = 'John Thorvald Wodder II'
__author_email__ = 'lineinfile@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://github.com/jwodder/lineinfile'

import re
import sys
from   typing import Optional, TYPE_CHECKING, Union

if sys.version_info[:2] >= (3,9):
    from re import Pattern
    List = list
else:
    from typing import List, Pattern

if TYPE_CHECKING:
    if sys.version_info[:2] >= (3, 8):
        from typing import Protocol
    else:
        from typing_extensions import Protocol

    class Locator(Protocol):
        def feed(self, i: int, line: str) -> None:
            ...

        def get_index(self) -> Optional[int]:
            ...


Patternish = Union[str, Pattern[str]]

LINE_ENDINGS = "\n\r"

class AtBOF:
    def feed(self, i: int, line: str) -> None:
        pass

    def get_index(self) -> Optional[int]:
        return 0


class AtEOF:
    def feed(self, i: int, line: str) -> None:
        pass

    def get_index(self) -> Optional[int]:
        return None


class AfterFirst:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern = _ensure_compiled(pattern)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.pattern.search(line):
            self.i = i+1

    def get_index(self) -> Optional[int]:
        return self.i


class AfterLast:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern = _ensure_compiled(pattern)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.pattern.search(line):
            self.i = i+1

    def get_index(self) -> Optional[int]:
        return self.i


class BeforeFirst:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern = _ensure_compiled(pattern)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.pattern.search(line):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


class BeforeLast:
    def __init__(self, pattern: Patternish) -> None:
        self.pattern: Pattern = _ensure_compiled(pattern)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.pattern.search(line):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


MatchFirst = BeforeFirst
MatchLast = BeforeLast


class MatchLineFirst:
    def __init__(self, line: str) -> None:
        self.line: str = line.rstrip(LINE_ENDINGS)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.i is None and self.line == line.rstrip(LINE_ENDINGS):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


class MatchLineLast:
    def __init__(self, line: str) -> None:
        self.line: str = line.rstrip(LINE_ENDINGS)
        self.i: Optional[int] = None

    def feed(self, i: int, line: str) -> None:
        if self.line == line.rstrip(LINE_ENDINGS):
            self.i = i

    def get_index(self) -> Optional[int]:
        return self.i


def add_line_to_string(
    s: str,
    line: str,
    regexp: Optional[Patternish] = None,
    locator: Optional["Locator"] = None,
    match_first: bool = False,
) -> str:
    line_matcher: "Locator"
    if match_first:
        line_matcher = MatchLineFirst(line)
    else:
        line_matcher = MatchLineLast(line)
    rgx: Optional["Locator"]
    if regexp is None:
        rgx = None
    elif match_first:
        rgx = MatchFirst(regexp)
    else:
        rgx = MatchLast(regexp)
    loccer = AtEOF() if locator is None else locator
    lines = ascii_splitlines(s)
    for i,ln in enumerate(lines):
        line_matcher.feed(i, ln)
        if rgx is not None:
            rgx.feed(i, ln)
        loccer.feed(i, ln)
    match_point = None if rgx is None else rgx.get_index()
    if match_point is None:
        match_point = line_matcher.get_index()
    if match_point is not None:
        assert match_point < len(lines)
        lines[match_point] = _ensure_terminated(line)
    else:
        insert_point = loccer.get_index()
        if insert_point is None:
            if lines:
                lines[-1] = _ensure_terminated(lines[-1])
            lines.append(_ensure_terminated(line))
        else:
            if lines and insert_point == len(lines):
                lines[-1] = _ensure_terminated(lines[-1])
            lines.insert(insert_point, _ensure_terminated(line))
    return ''.join(lines)

def _ensure_compiled(s_or_re: Patternish) -> Pattern:
    if isinstance(s_or_re, str):
        return re.compile(s_or_re)
    else:
        return s_or_re

def _ensure_terminated(s: str) -> str:
    if s.endswith(tuple(LINE_ENDINGS)):
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
