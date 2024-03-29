from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, TextIO
import click
from . import (
    ALWAYS,
    CHANGED,
    AfterFirst,
    AfterLast,
    AtBOF,
    AtEOF,
    BackupWhen,
    BeforeFirst,
    BeforeLast,
    __version__,
    add_line_to_file,
    add_line_to_string,
    remove_lines_from_file,
    remove_lines_from_string,
    unescape,
)

if TYPE_CHECKING:
    from . import Inserter


def set_inserter(ctx: click.Context, _param: click.Parameter, value: Any) -> Any:
    if value is not None:
        ctx.params["inserter"] = value
    return value


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    __version__,
    "-V",
    "--version",
    message="lineinfile %(version)s",
)
def main() -> None:
    """
    Add & remove lines in files by regex.

    Visit <https://github.com/jwodder/lineinfile> for more information.
    """
    pass


@main.command()
@click.option(
    "-a",
    "--after-first",
    metavar="REGEX",
    type=AfterFirst,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE after the first line matching REGEX",
)
@click.option(
    "-A",
    "--after-last",
    metavar="REGEX",
    type=AfterLast,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE after the last line matching REGEX",
)
@click.option(
    "-b",
    "--before-first",
    metavar="REGEX",
    type=BeforeFirst,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE before the first line matching REGEX",
)
@click.option(
    "-B",
    "--before-last",
    metavar="REGEX",
    type=BeforeLast,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE before the last line matching REGEX",
)
@click.option(
    "--bof",
    flag_value=AtBOF(),
    type=click.UNPROCESSED,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE at the beginning of the file",
)
@click.option(
    "--eof",
    flag_value=AtEOF(),
    type=click.UNPROCESSED,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE at the end of the file [default]",
)
@click.option(
    "-e",
    "--regexp",
    metavar="REGEX",
    help="Replace the last line matching REGEX with LINE",
)
@click.option(
    "--backrefs",
    is_flag=True,
    help="Use `--regexp` match to expand capturing groups in LINE",
)
@click.option(
    "--backup",
    "--backup-changed",
    "backup",
    flag_value=CHANGED,
    type=click.UNPROCESSED,
    help="Backup file if modified",
)
@click.option(
    "--backup-always",
    "backup",
    flag_value=ALWAYS,
    type=click.UNPROCESSED,
    help="Backup file whether modified or not",
)
@click.option(
    "-i",
    "--backup-ext",
    metavar="EXT",
    help="Extension for backup file [default: ~]",
)
@click.option(
    "-c",
    "--create",
    is_flag=True,
    help="Treat nonexistent FILE as empty",
)
@click.option(
    "-L",
    "--line",
    "line_opt",
    metavar="LINE",
    help="Use LINE as the line to insert",
)
@click.option(
    "-m/-M",
    "--match-first/--match-last",
    default=False,
    help="`--regexp` replaces first/last matching line in input [default: last]",
)
@click.option(
    "-o",
    "--outfile",
    type=click.File("w"),
    help="Write output to given file",
)
@click.argument("line", required=False)
@click.argument("file", required=False)
def add(
    line: Optional[str],
    file: Optional[str],
    line_opt: Optional[str],
    regexp: Optional[str],
    backrefs: bool,
    backup: Optional[BackupWhen],
    backup_ext: Optional[str],
    create: bool,
    match_first: bool,
    inserter: Optional[Inserter] = None,
    outfile: Optional[TextIO] = None,
) -> None:
    """
    Add LINE to FILE if it's not already present.

    If a Python regular expression is given with the `-e`/`--regexp`
    option and it matches any lines in the file, LINE will replace the last
    matching line (or the first matching line, if `--match-first` is given).
    If the regular expression does not match any lines (or no regular
    expression is specified) and LINE is not found in the file, the line is
    inserted at the end of the file by default; this can be changed with the
    `--after-first`, `--after-last`, `--before-first`, `--before-last`,
    and `--bof` options.

    If no file name is given on the command line, input is read from standard
    input, and the result is written to standard output.  It is an error to
    specify any of the `--backup-changed`, `--backup-always`, `--backup-ext`,
    or `--create` options when no file is given.
    """
    if backup_ext is not None and backup is None:
        backup = CHANGED
    if backrefs and regexp is None:
        raise click.UsageError("--backrefs cannot be specified without --regexp")
    if backup_ext == "":
        raise click.UsageError("--backup-ext cannot be empty")
    if line_opt is None:
        if line is None:
            raise click.UsageError("No LINE given")
        else:
            theline = line
        thefile = "-" if file is None else file
    else:
        theline = line_opt
        thefile = "-" if line is None else line
        if file is not None:
            raise click.UsageError("-L/--line given with too many positional arguments")
    if not backrefs:
        theline = unescape(theline)
    if thefile == "-" or outfile is not None:
        if thefile == "-":
            errmsg = "{option} cannot be set when reading from standard input."
        else:
            errmsg = "{option} is incompatible with --outfile."
        if backup_ext is not None:
            raise click.UsageError(errmsg.format(option="--backup-ext"))
        if backup is CHANGED:
            raise click.UsageError(errmsg.format(option="--backup-changed"))
        if backup is ALWAYS:
            raise click.UsageError(errmsg.format(option="--backup-always"))
        if create:
            raise click.UsageError(errmsg.format(option="--create"))
        with click.open_file(thefile, encoding="utf-8") as fp:
            before = fp.read()
        after = add_line_to_string(
            before,
            theline,
            regexp=regexp,
            inserter=inserter,
            match_first=match_first,
            backrefs=backrefs,
        )
        if outfile is None:
            outfp = click.get_text_stream("stdout")
        else:
            outfp = outfile
        # Don't use click.echo(), as it modifies ANSI sequences on Windows
        print(after, end="", file=outfp)
    else:
        add_line_to_file(
            thefile,
            theline,
            regexp=regexp,
            inserter=inserter,
            match_first=match_first,
            backrefs=backrefs,
            backup=backup,
            backup_ext=backup_ext,
            create=create,
            encoding="utf-8",
        )


@main.command()
@click.option(
    "--backup",
    "--backup-changed",
    "backup",
    flag_value=CHANGED,
    type=click.UNPROCESSED,
    help="Backup file if modified",
)
@click.option(
    "--backup-always",
    "backup",
    flag_value=ALWAYS,
    type=click.UNPROCESSED,
    help="Backup file whether modified or not",
)
@click.option(
    "-i",
    "--backup-ext",
    metavar="EXT",
    help="Extension for backup file [default: ~]",
)
@click.option(
    "-e",
    "--regexp",
    "regexp_opt",
    metavar="REGEX",
    help="Delete lines matching REGEX",
)
@click.option(
    "-o",
    "--outfile",
    type=click.File("w"),
    help="Write output to given file",
)
@click.argument("regexp", required=False)
@click.argument("file", required=False)
def remove(
    regexp: Optional[str],
    file: Optional[str],
    regexp_opt: Optional[str],
    backup: Optional[BackupWhen],
    backup_ext: Optional[str],
    outfile: Optional[TextIO] = None,
) -> None:
    """
    Delete all lines from FILE that match REGEXP.

    If no file name is given on the command line, input is read from standard
    input, and the result is written to standard output.  It is an error to
    specify any of the `--backup-changed`, `--backup-always`, or `--backup-ext`
    options when no file is given.
    """
    if backup_ext is not None and backup is None:
        backup = CHANGED
    if backup_ext == "":
        raise click.UsageError("--backup-ext cannot be empty")
    if regexp_opt is None:
        if regexp is None:
            raise click.UsageError("No REGEXP given")
        else:
            theregexp = regexp
        thefile = "-" if file is None else file
    else:
        theregexp = regexp_opt
        thefile = "-" if regexp is None else regexp
        if file is not None:
            raise click.UsageError(
                "-e/--regexp given with too many positional arguments"
            )
    if thefile == "-" or outfile is not None:
        if thefile == "-":
            errmsg = "{option} cannot be set when reading from standard input."
        else:
            errmsg = "{option} is incompatible with --outfile."
        if backup_ext is not None:
            raise click.UsageError(errmsg.format(option="--backup-ext"))
        if backup is CHANGED:
            raise click.UsageError(errmsg.format(option="--backup-changed"))
        if backup is ALWAYS:
            raise click.UsageError(errmsg.format(option="--backup-always"))
        with click.open_file(thefile, encoding="utf-8") as fp:
            before = fp.read()
        after = remove_lines_from_string(before, theregexp)
        if outfile is None:
            outfp = click.get_text_stream("stdout")
        else:
            outfp = outfile
        # Don't use click.echo(), as it modifies ANSI sequences on Windows
        print(after, end="", file=outfp)
    else:
        remove_lines_from_file(
            thefile,
            theregexp,
            backup=backup,
            backup_ext=backup_ext,
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()  # pragma: no cover
