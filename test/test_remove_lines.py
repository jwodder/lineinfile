from   collections         import namedtuple
from   operator            import attrgetter
import os
from   pathlib             import Path
from   traceback           import format_exception
import click
from   click.testing       import CliRunner
import pytest
from   lineinfile          import ALWAYS, CHANGED, remove_lines_from_file, \
                                remove_lines_from_string
from   lineinfile.__main__ import main

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

def show_result(r):
    if r.exception is not None:
        return ''.join(format_exception(*r.exc_info))
    else:
        return r.output

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

CLI_DEFAULTS = {
    "backup": None,
    "backup_ext": None,
}

@pytest.mark.parametrize('opts,args', [
    ([], {}),
    (["--backup"], {"backup": CHANGED}),
    (["--backup-changed"], {"backup": CHANGED}),
    (["--backup", "-i.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["-i.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["--backup-ext=.bak"], {"backup": CHANGED, "backup_ext": ".bak"}),
    (["--backup-always"], {"backup": ALWAYS}),
    (["--backup-always", "-i.bak"], {"backup": ALWAYS, "backup_ext": ".bak"}),
    (["-i.bak", "--backup-always"], {"backup": ALWAYS, "backup_ext": ".bak"}),
    (["--backup-changed", "--backup-always"], {"backup": ALWAYS}),
    (["--backup-always", "--backup-changed"], {"backup": CHANGED}),
])
def test_cli_remove(opts, args, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["remove"] + opts + ["^foo=", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ''
    fargs = {**CLI_DEFAULTS, **args}
    remove_lines_mock.assert_called_once_with("file.txt", "^foo=", **fargs)

def test_cli_remove_empty_backup_ext(mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["remove", "--backup-ext=", "^foo=", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "--backup-ext cannot be empty"
    remove_lines_mock.assert_not_called()

@pytest.mark.parametrize('input_args', [[], ["-"]])
def test_cli_remove_stdin(input_args, mocker):
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        Path("-").touch()
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
            return_value=True,
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "^foo="] + input_args,
            input=INPUT,
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")

@pytest.mark.parametrize('input_args', [[], ["-"]])
@pytest.mark.parametrize('file_arg,err_arg', [
    ("--backup", "--backup-changed"),
    ("--backup-changed", "--backup-changed"),
    ("--backup-always", "--backup-always"),
    ("-i.bak", "--backup-ext"),
])
def test_cli_remove_stdin_bad_file_args(file_arg, err_arg, input_args, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
        )
        r = runner.invoke(
            main,
            ["remove", file_arg, "^gnusto="] + input_args,
            input='This is test text.\n',
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == (
        f"{err_arg} cannot be set when reading from standard input."
    )
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_not_called()

def test_cli_remove_outfile(mocker):
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "--outfile=out.txt", "^foo=", "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ''
        assert sorted(os.listdir()) == ["file.txt", "out.txt"]
        assert thefile.read_text() == INPUT
        assert Path("out.txt").read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")

@pytest.mark.parametrize('input_args', [[], ["-"]])
def test_cli_remove_stdin_outfile(input_args, mocker):
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        Path("-").touch()
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "-oout.txt", "^foo="] + input_args,
            input=INPUT,
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ''
        assert sorted(os.listdir()) == ["-", "out.txt"]
        assert Path("-").read_text() == ''
        assert Path("out.txt").read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")

def test_cli_remove_outfile_stdout(mocker):
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "--outfile", "-", "^foo=", "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == output
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == INPUT
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")

@pytest.mark.parametrize('file_arg,err_arg', [
    ("--backup", "--backup-changed"),
    ("--backup-changed", "--backup-changed"),
    ("--backup-always", "--backup-always"),
    ("-i.bak", "--backup-ext"),
])
def test_cli_remove_outfile_bad_file_args(file_arg, err_arg, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
        )
        r = runner.invoke(
            main,
            ["remove", "-o", "out.txt", file_arg, "^foo=", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == f"{err_arg} is incompatible with --outfile."
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_not_called()

def test_cli_remove_outfile_is_infile(mocker):
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_file',
        )
        remove_lines_str_mock = mocker.patch(
            'lineinfile.__main__.remove_lines_from_string',
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "--outfile=file.txt", "^foo=", "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ''
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")
