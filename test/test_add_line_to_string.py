from   pathlib    import Path
import pytest
from   lineinfile import add_line_to_string

CASES_DIR = Path(__file__).with_name('data') / 'add_line_to_string'

INPUT = (CASES_DIR / 'input.txt').read_text()

def gentestcases():
    for cfgfile in CASES_DIR.glob("*.py"):
        cfg = {}
        exec(cfgfile.read_text(), cfg)
        try:
            input_file = cfg["input_file"]
        except KeyError:
            source = INPUT
        else:
            source = (CASES_DIR / input_file).read_text()
        output = cfgfile.with_suffix('.txt').read_text()
        yield pytest.param(
            source, cfg["line"], cfg["args"], output,
            id=cfgfile.with_suffix('').name,
        )

@pytest.mark.parametrize('source,line,args,output', gentestcases())
def test_add_line_to_string(source, line, args, output):
    assert add_line_to_string(source, line, **args) == output
