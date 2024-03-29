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
    AfterFirst,
    AfterLast,
    AtBOF,
    AtEOF,
    BackupWhen,
    BeforeFirst,
    BeforeLast,
    Inserter,
    add_line_to_file,
    add_line_to_string,
    ensure_terminated,
)
import lineinfile.__main__
from lineinfile.__main__ import main

CASES_DIR = Path(__file__).with_name("data") / "add_line"

INPUT = (CASES_DIR / "input.txt").read_text()


@dataclass
class AddLineCase:
    name: str
    input: str
    line: str
    args: dict[str, Any]
    options: list[str]
    output: str
    nonuniversal_lines: bool

    @property
    def changed(self) -> bool:
        return self.input != self.output


# The set of test cases has to be fetched anew for every test because the
# inserters contain mutable state.


def add_line_cases() -> Iterator[AddLineCase]:
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
        yield AddLineCase(
            name=cfgfile.with_suffix("").name,
            input=source,
            line=cfg["line"],
            args=cfg["args"],
            options=cfg["options"],
            output=output,
            nonuniversal_lines=cfg.get("nonuniversal_lines", False),
        )


def file_add_line_cases() -> Iterator[AddLineCase]:
    for c in add_line_cases():
        if not c.nonuniversal_lines:
            yield c


def listdir(dirpath: Path) -> list[str]:
    return sorted(p.name for p in dirpath.iterdir())


def show_result(r: Result) -> str:
    if r.exception is not None:
        assert isinstance(r.exc_info, tuple)
        return "".join(format_exception(*r.exc_info))
    else:
        return r.output


@pytest.mark.parametrize("case", add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_string(case: AddLineCase) -> None:
    assert add_line_to_string(case.input, case.line, **case.args) == case.output


def test_backrefs_no_regexp() -> None:
    with pytest.raises(ValueError) as excinfo:
        add_line_to_string(INPUT, "gnusto=cleesh", backrefs=True)
    assert str(excinfo.value) == "backrefs=True cannot be given without regexp"


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file(case: AddLineCase, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert add_line_to_file(thefile, case.line, **case.args) == case.changed
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file_backup_changed(case: AddLineCase, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        add_line_to_file(thefile, case.line, **case.args, backup=CHANGED)
        == case.changed
    )
    if case.changed:
        assert listdir(tmp_path) == ["file.txt", "file.txt~"]
        assert thefile.with_name(thefile.name + "~").read_text() == case.input
    else:
        assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file_backup_changed_custom_ext(
    case: AddLineCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        add_line_to_file(
            thefile,
            case.line,
            **case.args,
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


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file_backup_always(case: AddLineCase, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        add_line_to_file(thefile, case.line, **case.args, backup=ALWAYS) == case.changed
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.with_name(thefile.name + "~").read_text() == case.input
    assert thefile.read_text() == case.output


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_add_line_to_file_backup_always_custom_ext(
    case: AddLineCase, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(case.input)
    assert (
        add_line_to_file(
            thefile,
            case.line,
            **case.args,
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
        add_line_to_file(
            "nonexistent.txt",
            "gnusto=cleesh",
            backup_ext="",
            backup=when,
        )
    assert str(excinfo.value) == "Cannot use empty string as backup_ext"


def test_file_line_replaces_self(tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    assert not add_line_to_file(
        thefile,
        "bar=quux\n",
        regexp=r"^bar=",
        backup=CHANGED,
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == INPUT


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_backup_file_exists(tmp_path: Path, when: BackupWhen) -> None:
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


@pytest.mark.parametrize("create", [False, True])
def test_create_file_exists(tmp_path: Path, create: bool) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT)
    assert add_line_to_file(thefile, "gnusto=cleesh", create=create)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == INPUT + "gnusto=cleesh\n"


def test_no_create_file_not_exists(tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    with pytest.raises(FileNotFoundError):
        add_line_to_file(thefile, "gnusto=cleesh")
    assert listdir(tmp_path) == []


def test_create_file_not_exists(tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    assert add_line_to_file(thefile, "gnusto=cleesh", create=True)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == "gnusto=cleesh\n"


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_create_file_not_exists_backup(tmp_path: Path, when: BackupWhen) -> None:
    thefile = tmp_path / "file.txt"
    assert add_line_to_file(thefile, "gnusto=cleesh", create=True, backup=when)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == "gnusto=cleesh\n"


def test_create_file_no_change(tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    assert not add_line_to_file(
        thefile,
        r"\1=cleesh",
        regexp=r"^(\w+)=",
        backrefs=True,
        create=True,
    )
    assert listdir(tmp_path) == []


@pytest.mark.parametrize("when", [CHANGED, ALWAYS])
def test_backup_symlink(tmp_path: Path, when: BackupWhen) -> None:
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


def test_backup_symlink_no_change(tmp_path: Path) -> None:
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


STRING_DEFAULTS = {
    "regexp": None,
    "backrefs": False,
    "match_first": False,
    "inserter": None,
}

CLI_DEFAULTS = {
    **STRING_DEFAULTS,
    "backup": None,
    "backup_ext": None,
    "create": False,
    "encoding": "utf-8",
}


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
@pytest.mark.parametrize(
    "backup_opts,backup_args",
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
        (["--create"], {"create": True}),
    ],
)
def test_cli_add(
    case: AddLineCase,
    backup_opts: list[str],
    backup_args: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=case.changed,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + backup_opts + [case.line, "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    args = {**CLI_DEFAULTS, **case.args, **backup_args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_mock.assert_called_once_with("file.txt", case.line, **args)


@pytest.mark.parametrize(
    "backup_opts,backup_args",
    [
        ([], {}),
        (["--create"], {"create": True}),
    ],
)
def test_cli_add_file_not_exists_no_error(
    backup_opts: list[str], backup_args: dict[str, Any], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add"] + backup_opts + ["gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    args = {**CLI_DEFAULTS, **backup_args}
    add_line_mock.assert_called_once_with("file.txt", "gnusto=cleesh", **args)


@pytest.mark.parametrize(
    "opts,inserter",
    [
        ([], None),
        (["--after-first", "foo"], AfterFirst("foo")),
        (["--after-first", "foo", "--before-last", "bar"], BeforeLast("bar")),
        (["-B", "bar", "-a", "foo"], AfterFirst("foo")),
        (["--bof"], AtBOF()),
        (["--bof", "-A", "foo"], AfterLast("foo")),
        (["-A", "foo", "--bof"], AtBOF()),
        (["--bof", "--eof"], AtEOF()),
        (["--eof", "--bof"], AtBOF()),
        (["--bof", "--eof", "-b", "foo"], BeforeFirst("foo")),
        (["-a", "foo", "-A", "bar", "-b", "baz", "-B", "quux"], BeforeLast("quux")),
        (
            ["-a", "foo", "-A", "bar", "--bof", "-b", "baz", "-B", "quux"],
            BeforeLast("quux"),
        ),
        (["-a", "foo", "-a", "bar"], AfterFirst("bar")),
        pytest.param(
            ["-a", "foo", "-b", "quux", "-a", "bar"],
            AfterFirst("bar"),
            marks=pytest.mark.xfail(reason="Click doesn't work that way."),
        ),
    ],
)
def test_cli_add_inserter_options(
    opts: list[str], inserter: Inserter | None, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add"] + opts + ["gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    args = {**CLI_DEFAULTS, "inserter": inserter}
    add_line_mock.assert_called_once_with("file.txt", "gnusto=cleesh", **args)


@pytest.mark.parametrize(
    "opts,match_first",
    [
        ([], False),
        (["--match-first"], True),
        (["--match-last"], False),
        (["-m", "-M"], False),
        (["-M", "-m"], True),
        (["-m", "-M", "-m"], True),
        (["-M", "-m", "-M"], False),
    ],
)
def test_cli_add_match_options(
    opts: list[str], match_first: bool, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add"] + opts + ["gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    args = {**CLI_DEFAULTS, "match_first": match_first}
    add_line_mock.assert_called_once_with("file.txt", "gnusto=cleesh", **args)


def test_cli_add_backrefs_no_regex(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add", "--backrefs", "gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "--backrefs cannot be specified without --regexp"
    add_line_mock.assert_not_called()


def test_cli_add_empty_backup_ext(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add", "--backup-ext=", "gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "--backup-ext cannot be empty"
    add_line_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_add_stdin(
    case: AddLineCase, input_args: list[str], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("-").touch()
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=case.changed,
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=case.output,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + [case.line] + input_args,
            input=case.input,
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == case.output
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize("input_args", [[], ["-"]])
@pytest.mark.parametrize(
    "file_arg,err_arg",
    [
        ("--backup", "--backup-changed"),
        ("--backup-changed", "--backup-changed"),
        ("--backup-always", "--backup-always"),
        ("-i.bak", "--backup-ext"),
        ("--create", "--create"),
    ],
)
def test_cli_add_stdin_bad_file_args(
    file_arg: str, err_arg: str, input_args: list[str], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
        )
        r = runner.invoke(
            main,
            ["add", file_arg, "gnusto=cleesh"] + input_args,
            input="This is test text.\n",
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == (
        f"{err_arg} cannot be set when reading from standard input."
    )
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile(case: AddLineCase, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(case.input)
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=case.output,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + ["--outfile=out.txt", case.line, "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert sorted(os.listdir()) == ["file.txt", "out.txt"]
        assert thefile.read_text() == case.input
        assert Path("out.txt").read_text() == case.output
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_add_stdin_outfile(
    case: AddLineCase, input_args: list[str], mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("-").touch()
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=case.changed,
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=case.output,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + ["-oout.txt", case.line] + input_args,
            input=case.input,
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert sorted(os.listdir()) == ["-", "out.txt"]
        assert Path("-").read_text() == ""
        assert Path("out.txt").read_text() == case.output
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile_stdout(case: AddLineCase, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(case.input)
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=case.output,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + ["--outfile", "-", case.line, "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == case.output
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == case.input
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize(
    "file_arg,err_arg",
    [
        ("--backup", "--backup-changed"),
        ("--backup-changed", "--backup-changed"),
        ("--backup-always", "--backup-always"),
        ("-i.bak", "--backup-ext"),
        ("--create", "--create"),
    ],
)
def test_cli_add_outfile_bad_file_args(
    file_arg: str, err_arg: str, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
        )
        r = runner.invoke(
            main,
            ["add", "-o", "out.txt", file_arg, "gnusto=cleesh", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == f"{err_arg} is incompatible with --outfile."
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile_is_infile(case: AddLineCase, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(case.input)
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=case.output,
        )
        r = runner.invoke(
            main,
            ["add"] + case.options + ["--outfile=file.txt", case.line, "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == case.output
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize(
    "escline,line",
    [
        ("foo", "foo"),
        (r"foo\n", "foo\n"),
        (r"foo\\n", "foo\\n"),
        (r"foo\\\n", "foo\\\n"),
        (r"foo\012", "foo\n"),
        (r"foo\x0A", "foo\n"),
        (r"foo\u000A", "foo\n"),
        (r"foo\\bar", r"foo\bar"),
        (r"foo\'bar", "foo'bar"),
        (r"foo\"bar", 'foo"bar'),
        (r"foo\abar", "foo\abar"),
        (r"foo\bbar", "foo\bbar"),
        (r"foo\fbar", "foo\fbar"),
        (r"foo\tbar", "foo\tbar"),
        (r"foo\vbar", "foo\vbar"),
        (r"\U0001F410", "\U0001F410"),
        ("åéîøü", "åéîøü"),
        (r"\u2603", "\u2603"),
        ("\u2603", "\u2603"),
        ("\U0001F410", "\U0001F410"),
        (r"\N{SNOWMAN}", "\u2603"),
    ],
)
def test_cli_add_backslashed(escline: str, line: str, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT)
        add_line_file_spy = mocker.spy(lineinfile.__main__, "add_line_to_file")
        r = runner.invoke(
            main,
            ["add", escline, "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == INPUT + ensure_terminated(line)
    add_line_file_spy.assert_called_once_with("file.txt", line, **CLI_DEFAULTS)


@pytest.mark.parametrize(
    "escline,line",
    [
        ("foo", "foo"),
        (r"foo\n", "foo\n"),
        (r"foo\\n", "foo\\n"),
        (r"foo\\\n", "foo\\\n"),
        (r"foo\012", "foo\n"),
        pytest.param(
            r"foo\x0A",
            "foo\n",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        pytest.param(
            r"foo\u000A",
            "foo\n",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        (r"foo\\bar", r"foo\bar"),
        pytest.param(
            r"foo\'bar",
            "foo'bar",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        pytest.param(
            r"foo\"bar",
            'foo"bar',
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        (r"foo\abar", "foo\abar"),
        (r"foo\bbar", "foo\bbar"),
        (r"foo\fbar", "foo\fbar"),
        (r"foo\tbar", "foo\tbar"),
        (r"foo\vbar", "foo\vbar"),
        pytest.param(
            r"\U0001F410",
            "\U0001F410",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        ("åéîøü", "åéîøü"),
        pytest.param(
            r"\u2603",
            "\u2603",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        ("\u2603", "\u2603"),
        ("\U0001F410", "\U0001F410"),
        pytest.param(
            r"\N{SNOWMAN}",
            "\u2603",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
    ],
)
def test_cli_add_backslashed_backrefs(
    escline: str, line: str, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        thefile = Path("file.txt")
        thefile.write_text(INPUT + "replaceme\n")
        add_line_file_spy = mocker.spy(lineinfile.__main__, "add_line_to_file")
        r = runner.invoke(
            main,
            ["add", "--backrefs", "-e", "replaceme", escline, "file.txt"],
            standalone_mode=False,
        )
        assert r.exit_code == 0, show_result(r)
        assert r.output == ""
        assert os.listdir() == ["file.txt"]
        assert thefile.read_text() == INPUT + ensure_terminated(line)
    args = {**CLI_DEFAULTS, "regexp": "replaceme", "backrefs": True}
    add_line_file_spy.assert_called_once_with("file.txt", escline, **args)


@pytest.mark.parametrize(
    "line",
    [
        "gnusto=cleesh",
        "-ecleesh",
        "--gnusto=cleesh",
    ],
)
def test_cli_add_line_opt_file(line: str, mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add", "-L", line, "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    add_line_mock.assert_called_once_with("file.txt", line, **CLI_DEFAULTS)


@pytest.mark.parametrize(
    "line",
    [
        "gnusto=cleesh",
        "-ecleesh",
        "--gnusto=cleesh",
    ],
)
@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_add_line_opt_stdin(
    input_args: list[str], line: str, mocker: MockerFixture
) -> None:
    runner = CliRunner()
    output = INPUT + line + "\n"
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_file_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        add_line_str_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_string",
            return_value=output,
        )
        r = runner.invoke(
            main,
            ["add", "-L", line] + input_args,
            input=INPUT,
            standalone_mode=False,
        )
    assert r.exit_code == 0, show_result(r)
    assert r.output == output
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(INPUT, line, **STRING_DEFAULTS)


def test_cli_add_line_opt_two_args(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("file.txt").touch()
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(
            main,
            ["add", "--line", "gnusto=cleesh", "foo=bar", "file.txt"],
            standalone_mode=False,
        )
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "-L/--line given with too many positional arguments"
    add_line_mock.assert_not_called()


def test_cli_add_no_line_opt_no_args(mocker: MockerFixture) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        add_line_mock = mocker.patch(
            "lineinfile.__main__.add_line_to_file",
            return_value=True,
        )
        r = runner.invoke(main, ["add"], standalone_mode=False)
    assert r.exit_code != 0
    assert isinstance(r.exception, click.UsageError)
    assert str(r.exception) == "No LINE given"
    add_line_mock.assert_not_called()


def test_add_line_to_file_encoding(mocker: MockerFixture, tmp_path: Path) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(INPUT, encoding="utf-16")
    add_line_str_spy = mocker.spy(lineinfile, "add_line_to_string")
    assert add_line_to_file(thefile, "gnusto=cleesh", encoding="utf-16")
    add_line_str_spy.assert_called_once_with(
        INPUT,
        "gnusto=cleesh",
        **STRING_DEFAULTS,
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text(encoding="utf-16") == INPUT + "gnusto=cleesh\n"


def test_add_line_to_file_encoding_errors(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n",
        encoding="latin-1",
    )
    add_line_str_spy = mocker.spy(lineinfile, "add_line_to_string")
    assert add_line_to_file(
        thefile,
        "edh=\xF0",
        encoding="utf-8",
        errors="surrogateescape",
    )
    add_line_str_spy.assert_called_once_with(
        "edh=\uDCF0\na-tilde-degrees=\xF0\n",
        "edh=\xF0",
        **STRING_DEFAULTS,
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text(encoding="latin-1") == (
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\nedh=\xC3\xB0\n"
    )


def test_add_line_to_file_encoding_errors_backup(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n",
        encoding="latin-1",
    )
    add_line_str_spy = mocker.spy(lineinfile, "add_line_to_string")
    assert add_line_to_file(
        thefile,
        "edh=\xF0",
        encoding="utf-8",
        errors="surrogateescape",
        backup=CHANGED,
    )
    add_line_str_spy.assert_called_once_with(
        "edh=\uDCF0\na-tilde-degrees=\xF0\n",
        "edh=\xF0",
        **STRING_DEFAULTS,
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.read_text(encoding="latin-1") == (
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\nedh=\xC3\xB0\n"
    )
    assert thefile.with_name(thefile.name + "~").read_text(encoding="latin-1") == (
        "edh=\xF0\na-tilde-degrees=\xC3\xB0\n"
    )


def test_after_first_reusable() -> None:
    inserter = AfterFirst("^foo=")
    assert (
        add_line_to_string(
            "foo=bar\nbar=baz\nbaz=quux\n",
            "gnusto=cleesh",
            inserter=inserter,
        )
        == "foo=bar\ngnusto=cleesh\nbar=baz\nbaz=quux\n"
    )
    assert (
        add_line_to_string(
            "food=yummy\nfoo=icky\nfo=misspelled\n",
            "gnusto=cleesh",
            inserter=inserter,
        )
        == "food=yummy\nfoo=icky\ngnusto=cleesh\nfo=misspelled\n"
    )
