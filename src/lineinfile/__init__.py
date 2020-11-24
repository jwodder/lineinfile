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

# Line endings recognized by str.splitlines()
LINE_ENDINGS = "\n\r\v\f\x1C\x1D\x1E\x85\u2028\u2029"

class AtBOF:
    def feed(self, i, line):
        pass

    def get_index(self):
        return 0


class AtEOF:
    def feed(self, i, line):
        pass

    def get_index(self):
        return None


class AfterFirst:
    def __init__(self, pattern):
        self.pattern = _ensure_compiled(pattern)
        self.i = None

    def feed(self, i, line):
        if self.i is None and self.pattern.search(line):
            self.i = i+1

    def get_index(self):
        return self.i


class AfterLast:
    def __init__(self, pattern):
        self.pattern = _ensure_compiled(pattern)
        self.i = None

    def feed(self, i, line):
        if self.pattern.search(line):
            self.i = i+1

    def get_index(self):
        return self.i


class BeforeFirst:
    def __init__(self, pattern):
        self.pattern = _ensure_compiled(pattern)
        self.i = None

    def feed(self, i, line):
        if self.i is None and self.pattern.search(line):
            self.i = i

    def get_index(self):
        return self.i


class BeforeLast:
    def __init__(self, pattern):
        self.pattern = _ensure_compiled(pattern)
        self.i = None

    def feed(self, i, line):
        if self.pattern.search(line):
            self.i = i

    def get_index(self):
        return self.i


def add_line_to_string(s, line, locator=None):
    if locator is None:
        locator = AtEOF()
    lines = s.splitlines(keepends=True)
    line_stripped = line.rstrip(LINE_ENDINGS)
    for i,ln in enumerate(lines):
        if line_stripped == ln.rstrip(LINE_ENDINGS):
            return s
        else:
            locator.feed(i, ln)
    insert_point = locator.get_index()
    if insert_point is None:
        lines.append(_ensure_terminated(line))
    else:
        lines.insert(insert_point, _ensure_terminated(line))
    return ''.join(lines)

def _ensure_compiled(s_or_re):
    if isinstance(s_or_re, str):
        return re.compile(s_or_re)
    else:
        return s_or_re

def _ensure_terminated(s):
    if s.endswith(tuple(LINE_ENDINGS)):
        return s
    else:
        return s + '\n'
