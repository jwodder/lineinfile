from   collections         import namedtuple
from   operator            import attrgetter
from   pathlib             import Path
from   traceback           import format_exception
from   click.testing       import CliRunner
import pytest
from   lineinfile          import ALWAYS, CHANGED, add_line_to_file, \
                                    add_line_to_string
from   lineinfile.__main__ import main

CASES_DIR = Path(__file__).with_name('data') / 'add_line'

INPUT = (CASES_DIR / 'input.txt').read_text()

class AddLineCase(
    namedtuple(
        'AddLineCase', 'name input line args options output nonuniversal_lines',
    )
):
    @property
    def changed(self):
        return self.input != self.output

# The set of test cases has to be fetched anew for every test because the
# locators contain mutable state.

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
            options=cfg["options"],
            output=output,
            nonuniversal_lines=cfg.get("nonuniversal_lines", False),
        )

def file_add_line_cases():
    for c in add_line_cases():
        if not c.nonuniversal_lines:
            yield c

def listdir(dirpath):
    return sorted(p.name for p in dirpath.iterdir())

def show_result(r):
    if r.exception is not None:
        return ''.join(format_exception(*r.exc_info))
    else:
        return r.output

@pytest.mark.parametrize('case', add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_string(case):
    assert add_line_to_string(case.input, case.line, **case.args) == case.output

def test_backref_no_regexp():
    with pytest.raises(ValueError) as excinfo:
        add_line_to_string(INPUT, "gnusto=cleesh", backrefs=True)
    assert str(excinfo.value) == "backrefs=True cannot be given without regexp"

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args) == case.changed
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
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

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
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

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file_backup_always(case, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args, backup=ALWAYS) \
        == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.with_name(thefile.name + '~').read_text() == case.input
    assert thefile.read_text() == case.output

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
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

@pytest.mark.parametrize('when', [CHANGED, ALWAYS])
def test_backup_symlink(tmp_path, when):
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    linkfile = tmp_path / "link.txt"
    linkfile.symlink_to(thefile)
    assert add_line_to_file(
        linkfile,
        "gnusto=cleesh",
        backup=when,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "link.txt", "link.txt.bak"]
    assert linkfile.is_symlink()
    assert not (tmp_path / "link.txt.bak").is_symlink()
    assert (tmp_path / "link.txt.bak").read_text() == INPUT
    assert thefile.read_text() == INPUT + "gnusto=cleesh\n"

def test_backup_symlink_no_change(tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    linkfile = tmp_path / "link.txt"
    linkfile.symlink_to(thefile)
    assert not add_line_to_file(
        linkfile,
        "foo=apple",
        backup=ALWAYS,
        backup_ext=".bak",
    )
    assert listdir(tmp_path) == ["file.txt", "link.txt", "link.txt.bak"]
    assert linkfile.is_symlink()
    assert not (tmp_path / "link.txt.bak").is_symlink()
    assert (tmp_path / "link.txt.bak").read_text() == INPUT
    assert thefile.read_text() == INPUT

CLI_DEFAULTS = {
    "regexp": None,
    "backrefs": False,
    "backup": None,
    "backup_ext": None,
    "create": False,
    "match_first": False,
    "locator": None,
}

@pytest.mark.parametrize('case', file_add_line_cases(), ids=attrgetter("name"))
@pytest.mark.parametrize('backup_opts,backup_args', [
    ([], {}),
    (["--backup"], {"backup": CHANGED}),
    (["--backup-changed"], {"backup": CHANGED}),
    (["--backup", "-i.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["-i.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["--backup-ext=.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["--backup-always"], {"backup": ALWAYS}),
    (["--backup-always", "-i.bak"], {"backup": ALWAYS, "backup_ext": ".bak"}),
    (["-i.bak", "--backup-always"], {"backup": ALWAYS, "backup_ext": ".bak"}),
    (["--create"], {"create": True}),
])
def test_cli_add(case, backup_opts, backup_args, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            'lineinfile.__main__.add_line_to_file',
            return_value=case.changed,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + backup_opts + [case.line, "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ''
    args = {**CLI_DEFAULTS, **case.args, **backup_args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_mock.assert_called_once_with("file.txt", case.line, **args)

@pytest.mark.parametrize('backup_opts,backup_args', [
    ([], {}),
    (["--create"], {"create": True}),
])
def test_cli_add_file_not_exists_no_error(backup_opts, backup_args, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        add_line_mock = mocker.patch(
            'lineinfile.__main__.add_line_to_file',
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add"] + backup_opts + ["gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ''
    args = {**CLI_DEFAULTS, **backup_args}
    add_line_mock.assert_called_once_with("file.txt", "gnusto=cleesh", **args)
