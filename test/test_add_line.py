from   collections import namedtuple
from   operator    import attrgetter
from   pathlib     import Path
import pytest
from   lineinfile  import ALWAYS, CHANGED, add_line_to_file, add_line_to_string

CASES_DIR = Path(__file__).with_name('data') / 'add_line'

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

def listdir(dirpath):
    return sorted(p.name for p in dirpath.iterdir())

ADD_LINE_CASES = list(add_line_cases())

FILE_ADD_LINE_CASES = [c for c in ADD_LINE_CASES if not c.nonuniversal_lines]

@pytest.mark.parametrize('case', ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_string(case):
    assert add_line_to_string(case.input, case.line, **case.args) == case.output

def test_backref_no_regexp():
    with pytest.raises(ValueError) as excinfo:
        add_line_to_string(INPUT, "gnusto=cleesh", backrefs=True)
    assert str(excinfo.value) == "backrefs=True cannot be given without regexp"

@pytest.mark.parametrize('case', FILE_ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_file(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args) == case.changed
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', FILE_ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_file_backup_changed(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args, backup=CHANGED) \
        == case.changed
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt~"]
        assert thefile.with_name(thefile.name + '~').read_text() == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', FILE_ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_file_backup_changed_custom_ext(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(
        thefile,
        case.line,
        **case.args,
        backup=CHANGED,
        backup_ext='.bak',
    ) == case.changed
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
        assert thefile.with_name(thefile.name + '.bak').read_text() \
            == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', FILE_ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_file_backup_always(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args, backup=ALWAYS) \
        == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.with_name(thefile.name + '~').read_text() == case.input
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', FILE_ADD_LINE_CASES, ids=attrgetter("name"))
def test_add_line_to_file_backup_always_custom_ext(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(
        thefile,
        case.line,
        **case.args,
        backup=ALWAYS,
        backup_ext='.bak',
    ) == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
    assert thefile.with_name(thefile.name + '.bak').read_text() == case.input
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_empty_backup_ext(when):
    with pytest.raises(ValueError) as excinfo:
        add_line_to_file(
            "nonexistent.txt",
            "gnusto=cleesh",
            backup_ext='',
            backup=when,
        )
    assert str(excinfo.value) == "Cannot use empty string as backup_ext"

def test_file_line_replaces_self(tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    assert not add_line_to_file(
        thefile,
        "bar=quux\n",
        regexp=r'^bar=',
        backup=CHANGED,
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == INPUT

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_backup_file_exists(tmp_path, when):
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    (tmp_path / "file.txt.bak").write_text("This will be replaced.\n")
    assert add_line_to_file(
        thefile,
        "gnusto=cleesh",
        backup=when,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
    assert (tmp_path / "file.txt.bak").read_text() == INPUT
    assert thefile.read_text() == INPUT + "gnusto=cleesh\n"

@pytest.mark.parametrize('create', [False, True])
def test_create_file_exists(tmp_path, create):
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    assert add_line_to_file(thefile, "gnusto=cleesh", create=create)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == INPUT + "gnusto=cleesh\n"

def test_no_create_file_not_exists(tmp_path):
    thefile = tmp_path / "file.txt"
    with pytest.raises(FileNotFoundError):
        add_line_to_file(thefile, "gnusto=cleesh")
    assert listdir(tmp_path) == []

def test_create_file_not_exists(tmp_path):
    thefile = tmp_path / "file.txt"
    assert add_line_to_file(thefile, "gnusto=cleesh", create=True)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == "gnusto=cleesh\n"

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_create_file_not_exists_backup(tmp_path, when):
    thefile = tmp_path / "file.txt"
    assert add_line_to_file(thefile, "gnusto=cleesh", create=True, backup=when)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == "gnusto=cleesh\n"

def test_create_file_no_change(tmp_path):
    thefile = tmp_path / "file.txt"
    assert not add_line_to_file(
        thefile,
        r"\1=cleesh",
        regexp=r'^(\w+)=',
        backrefs=True,
        create=True,
    )
    assert listdir(tmp_path) == []