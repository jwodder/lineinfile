"""
Add & remove lines in files by regex

Visit <https://github.com/jwodder/lineinfile> for more information.
"""

__version__      = '0.1.0.dev1'
__author__       = 'John Thorvald Wodder II'
__author_email__ = 'lineinfile@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://github.com/jwodder/lineinfile'

class AtBOF:
    pass


class AtEOF:
    pass


class AfterFirst:
    def __init__(self, pattern):
        self.pattern = pattern


class AfterLast:
    def __init__(self, pattern):
        self.pattern = pattern


class BeforeFirst:
    def __init__(self, pattern):
        self.pattern = pattern


class BeforeLast:
    def __init__(self, pattern):
        self.pattern = pattern


def add_line_to_string(s, line, locator=None):
    raise NotImplementedError
