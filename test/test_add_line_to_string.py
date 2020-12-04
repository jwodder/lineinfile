from   pathlib    import Path
import pytest
from   lineinfile import add_line_to_string

CASES_DIR = Path(__file__).with_name('data') / 'add_line_to_string'

INPUT = (CASES_DIR / 'input.txt').read_text()

def gentestcases():
    for cfgfile in sorted(CASES_DIR.glob("*.py")):
        cfg = {}
        exec(cfgfile.read_text(), cfg)
        try:
            input_file = cfg["input_file"]
        except KeyError:
            source = INPUT
        else:
            with (CASES_DIR / input_file).open(newline='') as fp:
                source = fp.read()
        with cfgfile.with_suffix('.txt').open(newline='') as fp:
            output = fp.read()
        yield pytest.param(
            source, cfg["line"], cfg["args"], output,
            id=cfgfile.with_suffix('').name,
        )

@pytest.mark.parametrize('source,line,args,output', gentestcases())
def test_add_line_to_string(source, line, args, output):
    assert add_line_to_string(source, line, **args) == output

def test_backref_no_regexp():
    with pytest.raises(ValueError) as excinfo:
        add_line_to_string(INPUT, "gnusto=cleesh", backrefs=True)
    assert str(excinfo.value) == "backrefs=True cannot be given without regexp"
