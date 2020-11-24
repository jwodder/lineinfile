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
from   typing import Optional, Pattern, TYPE_CHECKING, Union

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


Patternish = Union[str, Pattern]

# Line endings recognized by str.splitlines()
LINE_ENDINGS = "\n\r\v\f\x1C\x1D\x1E\x85\u2028\u2029"

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


def add_line_to_string(s: str, line: str, locator: Optional["Locator"] = None) -> str:
    loccer = AtEOF() if locator is None else locator
    lines = s.splitlines(keepends=True)
    line_stripped = line.rstrip(LINE_ENDINGS)
    for i,ln in enumerate(lines):
        if line_stripped == ln.rstrip(LINE_ENDINGS):
            return s
        else:
            loccer.feed(i, ln)
    insert_point = loccer.get_index()
    if insert_point is None:
        lines.append(_ensure_terminated(line))
    else:
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
