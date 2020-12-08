from   collections import namedtuple
from   operator    import attrgetter
from   pathlib     import Path
import pytest
from   lineinfile  import ALWAYS, CHANGED, remove_lines_from_file, \
                            remove_lines_from_string

CASES_DIR = Path(__file__).with_name('data') / 'remove_lines'

INPUT = (CASES_DIR / 'input.txt').read_text()

class RemoveLinesCase(
    namedtuple('RemoveLinesCase', 'name input regexp output')
):
    @property
    def changed(self):
        return self.input != self.output

def remove_lines_cases():
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
        yield RemoveLinesCase(
            name=cfgfile.with_suffix('').name,
            input=source,
            regexp=cfg["regexp"],
            output=output,
        )

def listdir(dirpath):
    return sorted(p.name for p in dirpath.iterdir())

REMOVE_LINES_CASES = list(remove_lines_cases())

CHANGE_CASE = next(c for c in REMOVE_LINES_CASES if c.changed)
NO_CHANGE_CASE = next(c for c in REMOVE_LINES_CASES if not c.changed)

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_string(case):
    assert remove_lines_from_string(case.input, case.regexp) == case.output

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp) == case.changed
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_changed(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp, backup=CHANGED) \
        == case.changed
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt~"]
        assert thefile.with_name(thefile.name + '~').read_text() == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_changed_custom_ext(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(
        thefile,
        case.regexp,
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

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_always(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp, backup=ALWAYS) \
        == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.with_name(thefile.name + '~').read_text() == case.input
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_always_custom_ext(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(
        thefile,
        case.regexp,
        backup=ALWAYS,
        backup_ext='.bak',
    ) == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
    assert thefile.with_name(thefile.name + '.bak').read_text() == case.input
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_empty_backup_ext(when):
    with pytest.raises(ValueError) as excinfo:
        remove_lines_from_file(
            "nonexistent.txt",
            r'^gnusto=',
            backup_ext='',
            backup=when,
        )
    assert str(excinfo.value) == "Cannot use empty string as backup_ext"

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_backup_file_exists(tmp_path, when):
    thefile = tmp_path / "file.txt"
    thefile.write_text(CHANGE_CASE.input)
    (tmp_path / "file.txt.bak").write_text("This will be replaced.\n")
    assert remove_lines_from_file(
        thefile,
        CHANGE_CASE.regexp,
        backup=when,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
    assert (tmp_path / "file.txt.bak").read_text() == CHANGE_CASE.input
    assert thefile.read_text() == CHANGE_CASE.output

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_backup_symlink(tmp_path, when):
    thefile = tmp_path / "file.txt"
    thefile.write_text(CHANGE_CASE.input)
    linkfile = tmp_path / "link.txt"
    linkfile.symlink_to(thefile)
    assert remove_lines_from_file(
        linkfile,
        CHANGE_CASE.regexp,
        backup=when,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "link.txt", "link.txt.bak"]
    assert linkfile.is_symlink()
    assert not (tmp_path / "link.txt.bak").is_symlink()
    assert (tmp_path / "link.txt.bak").read_text() == CHANGE_CASE.input
    assert thefile.read_text() == CHANGE_CASE.output

def test_backup_symlink_no_change(tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(NO_CHANGE_CASE.input)
    linkfile = tmp_path / "link.txt"
    linkfile.symlink_to(thefile)
    assert not remove_lines_from_file(
        linkfile,
        NO_CHANGE_CASE.regexp,
        backup=ALWAYS,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "link.txt", "link.txt.bak"]
    assert linkfile.is_symlink()
    assert not (tmp_path / "link.txt.bak").is_symlink()
    assert (tmp_path / "link.txt.bak").read_text() == NO_CHANGE_CASE.input
    assert thefile.read_text() == NO_CHANGE_CASE.output
