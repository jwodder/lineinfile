from __future__ import annotations
from collections.abc import Iterator
from dataclasses import dataclass
from operator import attrgetter
import os
from pathlib import Path
from typing import Any
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
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    backup_opts: list[str],
    backup_args: dict[str, Any],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=case.changed,
    )
    assert main(["add"] + case.options + backup_opts + [case.line, "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    backup_opts: list[str],
    backup_args: dict[str, Any],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add"] + backup_opts + ["gnusto=cleesh", "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
        (
            ["-a", "foo", "-b", "quux", "-a", "bar"],
            AfterFirst("bar"),
        ),
    ],
)
def test_cli_add_inserter_options(
    capsys: pytest.CaptureFixture[str],
    opts: list[str],
    inserter: Inserter | None,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add"] + opts + ["gnusto=cleesh", "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    opts: list[str],
    match_first: bool,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add"] + opts + ["gnusto=cleesh", "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    args = {**CLI_DEFAULTS, "match_first": match_first}
    add_line_mock.assert_called_once_with("file.txt", "gnusto=cleesh", **args)


def test_cli_add_backrefs_no_regex(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add", "--backrefs", "gnusto=cleesh", "file.txt"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "lineinfile: --backrefs cannot be specified without --regexp\n"
    add_line_mock.assert_not_called()


def test_cli_add_empty_backup_ext(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add", "--backup-ext=", "gnusto=cleesh", "file.txt"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "lineinfile: --backup-ext cannot be empty\n"
    add_line_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
@pytest.mark.parametrize("input_args", [[], ["-"]])
def test_cli_add_stdin(
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    input_args: list[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mocker.patch("sys.stdin", **{"read.return_value": case.input})  # type: ignore[call-overload]
    monkeypatch.chdir(tmp_path)
    Path("-").touch()
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=case.changed,
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=case.output,
    )
    assert main(["add"] + case.options + [case.line] + input_args) == 0
    out, err = capsys.readouterr()
    assert out == case.output
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    file_arg: str,
    err_arg: str,
    input_args: list[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mocker.patch("sys.stdin", **{"read.return_value": "This is test text.\n"})  # type: ignore[call-overload]
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
    )
    assert main(["add", file_arg, "gnusto=cleesh"] + input_args) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert (
        err
        == f"lineinfile: {err_arg} cannot be set when reading from standard input.\n"
    )
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile(
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    thefile = Path("file.txt")
    thefile.write_text(case.input)
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=case.output,
    )
    assert (
        main(["add"] + case.options + ["--outfile=out.txt", case.line, "file.txt"]) == 0
    )
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    input_args: list[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mocker.patch("sys.stdin", **{"read.return_value": case.input})  # type: ignore[call-overload]
    monkeypatch.chdir(tmp_path)
    Path("-").touch()
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=case.changed,
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=case.output,
    )
    assert main(["add"] + case.options + ["-oout.txt", case.line] + input_args) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    assert sorted(os.listdir()) == ["-", "out.txt"]
    assert Path("-").read_text() == ""
    assert Path("out.txt").read_text() == case.output
    args = {**STRING_DEFAULTS, **case.args}
    if args["regexp"] is not None and not isinstance(args["regexp"], str):
        args["regexp"] = args["regexp"].pattern
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(case.input, case.line, **args)


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile_stdout(
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    thefile = Path("file.txt")
    thefile.write_text(case.input)
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=case.output,
    )
    assert main(["add"] + case.options + ["--outfile", "-", case.line, "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == case.output
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    file_arg: str,
    err_arg: str,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
    )
    assert main(["add", "-o", "out.txt", file_arg, "gnusto=cleesh", "file.txt"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == f"lineinfile: {err_arg} is incompatible with --outfile.\n"
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_not_called()


@pytest.mark.parametrize("case", file_add_line_cases(), ids=attrgetter("name"))
def test_cli_add_outfile_is_infile(
    capsys: pytest.CaptureFixture[str],
    case: AddLineCase,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    thefile = Path("file.txt")
    thefile.write_text(case.input)
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=case.output,
    )
    assert (
        main(["add"] + case.options + ["--outfile=file.txt", case.line, "file.txt"])
        == 0
    )
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
        (r"\U0001F410", "\U0001f410"),
        ("åéîøü", "åéîøü"),
        (r"\u2603", "\u2603"),
        ("\u2603", "\u2603"),
        ("\U0001f410", "\U0001f410"),
        (r"\N{SNOWMAN}", "\u2603"),
    ],
)
def test_cli_add_backslashed(
    capsys: pytest.CaptureFixture[str],
    escline: str,
    line: str,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    thefile = Path("file.txt")
    thefile.write_text(INPUT)
    add_line_file_spy = mocker.spy(lineinfile.__main__, "add_line_to_file")
    assert main(["add", escline, "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
            "\U0001f410",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        ("åéîøü", "åéîøü"),
        pytest.param(
            r"\u2603",
            "\u2603",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
        ("\u2603", "\u2603"),
        ("\U0001f410", "\U0001f410"),
        pytest.param(
            r"\N{SNOWMAN}",
            "\u2603",
            marks=pytest.mark.xfail(reason="Not supported by Match.expand()"),
        ),
    ],
)
def test_cli_add_backslashed_backrefs(
    capsys: pytest.CaptureFixture[str],
    escline: str,
    line: str,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    thefile = Path("file.txt")
    thefile.write_text(INPUT + "replaceme\n")
    add_line_file_spy = mocker.spy(lineinfile.__main__, "add_line_to_file")
    assert main(["add", "--backrefs", "-e", "replaceme", escline, "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
def test_cli_add_line_opt_file(
    capsys: pytest.CaptureFixture[str],
    line: str,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add", f"--line={line}", "file.txt"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
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
    capsys: pytest.CaptureFixture[str],
    input_args: list[str],
    line: str,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = INPUT + line + "\n"
    mocker.patch("sys.stdin", **{"read.return_value": INPUT})  # type: ignore[call-overload]
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_file_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    add_line_str_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_string",
        return_value=output,
    )
    assert main(["add", f"--line={line}"] + input_args) == 0
    out, err = capsys.readouterr()
    assert out == output
    assert err == ""
    add_line_file_mock.assert_not_called()
    add_line_str_mock.assert_called_once_with(INPUT, line, **STRING_DEFAULTS)


def test_cli_add_line_opt_two_args(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("file.txt").touch()
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add", "--line", "gnusto=cleesh", "foo=bar", "file.txt"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "lineinfile: -L/--line given with too many positional arguments\n"
    add_line_mock.assert_not_called()


def test_cli_add_no_line_opt_no_args(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    add_line_mock = mocker.patch(
        "lineinfile.__main__.add_line_to_file",
        return_value=True,
    )
    assert main(["add"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "lineinfile: No LINE given\n"
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
        "edh=\xf0\na-tilde-degrees=\xc3\xb0\n",
        encoding="latin-1",
    )
    add_line_str_spy = mocker.spy(lineinfile, "add_line_to_string")
    assert add_line_to_file(
        thefile,
        "edh=\xf0",
        encoding="utf-8",
        errors="surrogateescape",
    )
    add_line_str_spy.assert_called_once_with(
        "edh=\udcf0\na-tilde-degrees=\xf0\n",
        "edh=\xf0",
        **STRING_DEFAULTS,
    )
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text(encoding="latin-1") == (
        "edh=\xf0\na-tilde-degrees=\xc3\xb0\nedh=\xc3\xb0\n"
    )


def test_add_line_to_file_encoding_errors_backup(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    thefile = tmp_path / "file.txt"
    thefile.write_text(
        "edh=\xf0\na-tilde-degrees=\xc3\xb0\n",
        encoding="latin-1",
    )
    add_line_str_spy = mocker.spy(lineinfile, "add_line_to_string")
    assert add_line_to_file(
        thefile,
        "edh=\xf0",
        encoding="utf-8",
        errors="surrogateescape",
        backup=CHANGED,
    )
    add_line_str_spy.assert_called_once_with(
        "edh=\udcf0\na-tilde-degrees=\xf0\n",
        "edh=\xf0",
        **STRING_DEFAULTS,
    )
    assert listdir(tmp_path) == ["file.txt", "file.txt~"]
    assert thefile.read_text(encoding="latin-1") == (
        "edh=\xf0\na-tilde-degrees=\xc3\xb0\nedh=\xc3\xb0\n"
    )
    assert thefile.with_name(thefile.name + "~").read_text(encoding="latin-1") == (
        "edh=\xf0\na-tilde-degrees=\xc3\xb0\n"
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
