from   collections import namedtuple
from   operator    import attrgetter
from   pathlib     import Path
import pytest
from   lineinfile  import add_line_to_file, add_line_to_string

CASES_DIR = Path(__file__).with_name('data') / 'add_line_to_string'

INPUT = (CASES_DIR / 'input.txt').read_text()

class AddLineCase(
    namedtuple('AddLineCase', 'name input line args output nonuniversal_lines')
):
    @property
    def changed(self):
        return self.input != self.output

def add_line_cases():
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
        yield AddLineCase(
            name=cfgfile.with_suffix('').name,
            input=source,
            line=cfg["line"],
            args=cfg["args"],
            output=output,
            nonuniversal_lines=cfg.get("nonuniversal_lines", False),
        )

@pytest.mark.parametrize('case', add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_string(case):
    assert add_line_to_string(case.input, case.line, **case.args) == case.output

def test_backref_no_regexp():
    with pytest.raises(ValueError) as excinfo:
        add_line_to_string(INPUT, "gnusto=cleesh", backrefs=True)
    assert str(excinfo.value) == "backrefs=True cannot be given without regexp"

@pytest.mark.parametrize(
    'case',
    [c for c in add_line_cases() if not c.nonuniversal_lines],
    ids=attrgetter("name"),
)
def test_add_line_to_file(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args) == case.changed
    assert [p.name for p in tmp_path.iterdir()] == ["file.txt"]
    assert thefile.read_text() == case.output
