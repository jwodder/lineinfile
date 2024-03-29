from __future__ import annotations
from collections.abc import Iterator
from dataclasses import dataclass
from operator import attrgetter
import os
from pathlib import Path
from traceback import format_exception
from typing import Any
import click
from click.testing import CliRunner, Result
import pytest
from pytest_mock import MockerFixture
import lineinfile
from lineinfile import (
    ALWAYS,
    CHANGED,
    BackupWhen,
    remove_lines_from_file,
    remove_lines_from_string,
)
from lineinfile.__main__ import main

CASES_DIR = Path(__file__).with_name("data") / "remove_lines"

INPUT = (CASES_DIR / "input.txt").read_text()


@dataclass
class RemoveLinesCase:
    name: str
    input: str
    regexp: str
    output: str

    @property
    def changed(self) -> bool:
        return self.input != self.output


def remove_lines_cases() -> Iterator[RemoveLinesCase]:
    for cfgfile in sorted(CASES_DIR.glob("*.py")):
        cfg: dict[str, Any] = {}
        exec(cfgfile.read_text(), cfg)
        try:
            input_file = cfg["input_file"]
        except KeyError:
            source = INPUT
        else:
            with (CASES_DIR / input_file).open(newline="") as fp:
                source = fp.read()
        with cfgfile.with_suffix(".txt").open(newline="") as fp:
            output = fp.read()
        yield RemoveLinesCase(
            name=cfgfile.with_suffix("").name,
            input=source,
            regexp=cfg["regexp"],
            output=output,
        )


def listdir(dirpath: Path) -> list[str]:
    return sorted(p.name for p in dirpath.iterdir())


def show_result(r: Result) -> str:
    if r.exception is not None:
        assert isinstance(r.exc_info, tuple)
        return "".join(format_exception(*r.exc_info))
    else:
        return r.output


REMOVE_LINES_CASES = list(remove_lines_cases())

CHANGE_CASE = next(c for c in REMOVE_LINES_CASES if c.changed)
NO_CHANGE_CASE = next(c for c in REMOVE_LINES_CASES if not c.changed)


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_string(case: RemoveLinesCase) -> None:
    assert remove_lines_from_string(case.input, case.regexp) == case.output


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file(case: RemoveLinesCase, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp) == case.changed
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_changed(
    case: RemoveLinesCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp, backup=CHANGED) == case.changed
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt~"]
        assert thefile.with_name(thefile.name + "~").read_text() == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_changed_custom_ext(
    case: RemoveLinesCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        remove_lines_from_file(
            thefile,
            case.regexp,
            backup=CHANGED,
            backup_ext=".bak",
        )
        == case.changed
    )
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
        assert thefile.with_name(thefile.name + ".bak").read_text() == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_always(
    case: RemoveLinesCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert remove_lines_from_file(thefile, case.regexp, backup=ALWAYS) == case.changed
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.with_name(thefile.name + "~").read_text() == case.input
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", REMOVE_LINES_CASES, ids=attrgetter("name"))
def test_remove_lines_from_file_backup_always_custom_ext(
    case: RemoveLinesCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        remove_lines_from_file(
            thefile,
            case.regexp,
            backup=ALWAYS,
            backup_ext=".bak",
        )
        == case.changed
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt.bak"]
    assert thefile.with_name(thefile.name + ".bak").read_text() == case.input
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_empty_backup_ext(when: BackupWhen) -> None:
    with pytest.raises(ValueError) as excinfo:
        remove_lines_from_file(
            "nonexistent.txt",
            r"^gnusto=",
            backup_ext="",
            backup=when,
        )
    assert str(excinfo.value) == "Cannot use empty string as backup_ext"


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_backup_file_exists(tmp_path: Path, when: BackupWhen) -> None:
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


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_backup_symlink(tmp_path: Path, when: BackupWhen) -> None:
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


def test_backup_symlink_no_change(tmp_path: Path) -> None:
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
    "encoding": "utf-8",
}


@pytest.mark.parametrize(
    "opts,args",
    [
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
    ],
)
def test_cli_remove(
    opts: list[str], args: dict[str, Any], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["remove"] + opts + ["^foo=", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    fargs = {**CLI_DEFAULTS, **args}
    remove_lines_mock.assert_called_once_with("file.txt", "^foo=", **fargs)


def test_cli_remove_empty_backup_ext(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
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


@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_remove_stdin(input_args: list[str], mocker: MockerFixture) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        Path("-").touch()
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=True,
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
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


@pytest.mark.parametrize("input_args", [[], ["-"]])
@pytest.mark.parametrize(
    "file_arg,err_arg",
    [
        ("--backup", "--backup-changed"),
        ("--backup-changed", "--backup-changed"),
        ("--backup-always", "--backup-always"),
        ("-i.bak", "--backup-ext"),
    ],
)
def test_cli_remove_stdin_bad_file_args(
    file_arg: str, err_arg: str, input_args: list[str], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
        )
        r = runner.invoke(
            main,
            ["remove", file_arg, "^gnusto="] + input_args,
            input="This is test text.\n",
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == (
        f"{err_arg} cannot be set when reading from standard input."
    )
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_not_called()


def test_cli_remove_outfile(mocker: MockerFixture) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "--outfile=out.txt", "^foo=", "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert sorted(os.listdir()) == ["file.txt", "out.txt"]
        assert thefile.read_text() == INPUT
        assert Path("out.txt").read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")


@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_remove_stdin_outfile(input_args: list[str], mocker: MockerFixture) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        Path("-").touch()
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "-oout.txt", "^foo="] + input_args,
            input=INPUT,
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert sorted(os.listdir()) == ["-", "out.txt"]
        assert Path("-").read_text() == ""
        assert Path("out.txt").read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")


def test_cli_remove_outfile_stdout(mocker: MockerFixture) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
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


@pytest.mark.parametrize(
    "file_arg,err_arg",
    [
        ("--backup", "--backup-changed"),
        ("--backup-changed", "--backup-changed"),
        ("--backup-always", "--backup-always"),
        ("-i.bak", "--backup-ext"),
    ],
)
def test_cli_remove_outfile_bad_file_args(
    file_arg: str, err_arg: str, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
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


def test_cli_remove_outfile_is_infile(mocker: MockerFixture) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, "^foo=")
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "--outfile=file.txt", "^foo=", "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, "^foo=")


@pytest.mark.parametrize("regexp", ["^foo=", "-Lfoo=", "--foo=bar"])
def test_cli_remove_regexp_opt_file(regexp: str, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["remove", "-e", regexp, "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    remove_lines_mock.assert_called_once_with("file.txt", regexp, **CLI_DEFAULTS)


@pytest.mark.parametrize("regexp", ["^foo=", "-Lfoo=", "--foo=bar"])
@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_remove_regexp_opt_stdin(
    input_args: list[str], regexp: str, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    output = remove_lines_from_string(INPUT, regexp)
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_file_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=INPUT != output,
        )
        remove_lines_str_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_string",
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["remove", "-e", regexp] + input_args,
            input=INPUT,
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == output
    remove_lines_file_mock.assert_not_called()
    remove_lines_str_mock.assert_called_once_with(INPUT, regexp)


def test_cli_remove_regexp_opt_two_args(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        remove_lines_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["remove", "--regexp", "^gnusto=", "bar$", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "-e/--regexp given with too many positional arguments"
    remove_lines_mock.assert_not_called()


def test_cli_remove_no_regexp_opt_no_args(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        remove_lines_mock = mocker.patch(
            "lineinfile.__main__.remove_lines_from_file",
            return_value=True,
        )
        r = runner.invoke(main, ["remove"], standalone_mode=False)
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "No REGEXP given"
    remove_lines_mock.assert_not_called()


def test_remove_lines_from_file_encoding(mocker: MockerFixture, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT, encoding="utf-16")
    remove_lines_str_spy = mocker.spy(lineinfile, "remove_lines_from_string")
    assert remove_lines_from_file(thefile, "^foo", encoding="utf-16")
    remove_lines_str_spy.assert_called_once_with(INPUT, "^foo")
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text(encoding="utf-16") == remove_lines_from_string(
        INPUT, "^foo"
    )


def test_remove_lines_from_file_encoding_errors(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n",
        encoding="latin-1",
    )
    remove_lines_str_spy = mocker.spy(lineinfile, "remove_lines_from_string")
    assert remove_lines_from_file(
        thefile,
        "\uDCF0",
        encoding="utf-8",
        errors="surrogateescape",
    )
    remove_lines_str_spy.assert_called_once_with(
        "edh=\uDCF0\na-tilde-degrees=\xF0\n",
        "\uDCF0",
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text(encoding="latin-1") == "a-tilde-degrees=\xC3\xB0\n"


def test_remove_lines_from_file_encoding_errors_backup(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n",
        encoding="latin-1",
    )
    remove_lines_str_spy = mocker.spy(lineinfile, "remove_lines_from_string")
    assert remove_lines_from_file(
        thefile,
        "\xF0",
        encoding="utf-8",
        errors="surrogateescape",
        backup=CHANGED,
    )
    remove_lines_str_spy.assert_called_once_with(
        "edh=\uDCF0\na-tilde-degrees=\xF0\n",
        "\xF0",
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.read_text(encoding="latin-1") == "edh=\xF0\n"
    assert thefile.with_name(thefile.name + "~").read_text(encoding="latin-1") == (
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n"
    )
