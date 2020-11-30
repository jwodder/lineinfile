import pytest
from   lineinfile import ascii_splitlines, chomp, ensure_terminated

@pytest.mark.parametrize('s,lines', [
    ('', []),
    ('foobar', ['foobar']),
    ('foo\n', ['foo\n']),
    ('foo\r', ['foo\r']),
    ('foo\r\n', ['foo\r\n']),
    ('foo\n\r', ['foo\n', '\r']),
    ('foo\nbar', ['foo\n', 'bar']),
    ('foo\rbar', ['foo\r', 'bar']),
    ('foo\r\nbar', ['foo\r\n', 'bar']),
    ('foo\n\rbar', ['foo\n', '\r', 'bar']),
    ('foo\n\nbar', ['foo\n', '\n', 'bar']),
    ('foo\n\nbar\n', ['foo\n', '\n', 'bar\n']),
    (
        'Why\vare\fthere\x1Cso\x1Ddang\x1Emany\x85line\u2028separator\u2029'
        'characters?',
        ['Why\vare\fthere\x1Cso\x1Ddang\x1Emany\x85line\u2028separator\u2029'
         'characters?'],
    ),
])
def test_ascii_splitlines(s, lines):
    assert ascii_splitlines(s) == lines

@pytest.mark.parametrize('s,chomped', [
    ('foobar', 'foobar'),
    ('foobar\n', 'foobar'),
    ('foobar\r\n', 'foobar'),
    ('foobar\r', 'foobar'),
    ('foobar\n\r', 'foobar\n'),
    ('foobar\n\n', 'foobar\n'),
    ('foobar\nbaz', 'foobar\nbaz'),
])
def test_chomp(s, chomped):
    assert chomp(s) == chomped

@pytest.mark.parametrize('s,terminated', [
    ('foobar', 'foobar\n'),
    ('foobar\n', 'foobar\n'),
    ('foobar\r', 'foobar\r'),
    ('foobar\r\n', 'foobar\r\n'),
    ('foobar\n\r', 'foobar\n\r'),
    ('foo\nbar', 'foo\nbar\n'),
])
def test_ensure_terminated(s, terminated):
    assert ensure_terminated(s) == terminated
