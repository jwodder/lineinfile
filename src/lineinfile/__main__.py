from   typing import Any, Optional, TYPE_CHECKING, TextIO
import click
from   .      import (
    ALWAYS, AfterFirst, AfterLast, AtBOF, AtEOF, BackupWhen, BeforeFirst,
    BeforeLast, CHANGED, __version__, add_line_to_file, add_line_to_string,
    remove_lines_from_file, remove_lines_from_string,
)

if TYPE_CHECKING:
    from . import Inserter

def set_inserter(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    if value is not None:
        ctx.params["inserter"] = value
    return value

@click.group()
@click.version_option(
    __version__,
    '-V', '--version',
    message='lineinfile %(version)s',
)
def main() -> None:
    """
    Add & remove lines in files by regex.

    Visit <https://github.com/jwodder/lineinfile> for more information.
    """
    pass

@main.command()
@click.option(
    '-a', '--after-first',
    metavar='REGEX',
    type=AfterFirst,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE after the first line matching REGEX",
)
@click.option(
    '-A', '--after-last',
    metavar='REGEX',
    type=AfterLast,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE after the last line matching REGEX",
)
@click.option(
    '-b', '--before-first',
    metavar='REGEX',
    type=BeforeFirst,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE before the first line matching REGEX",
)
@click.option(
    '-B', '--before-last',
    metavar='REGEX',
    type=BeforeLast,
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE before the last line matching REGEX",
)
@click.option(
    '--bof',
    flag_value=AtBOF(),
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE at the beginning of the file",
)
@click.option(
    '--eof',
    flag_value=AtEOF(),
    callback=set_inserter,
    expose_value=False,
    help="Insert LINE at the end of the file [default]",
)
@click.option(
    '-e', '--regexp',
    metavar='REGEX',
    help="Replace the last line matching REGEX with LINE",
)
@click.option(
    '--backrefs',
    is_flag=True,
    help="Use `--regexp` match to expand capturing groups in LINE",
)
@click.option(
    '--backup', '--backup-changed', 'backup',
    flag_value=CHANGED,
    help="Backup file if modified",
)
@click.option(
    '--backup-always', 'backup',
    flag_value=ALWAYS,
    help="Backup file whether modified or not"
)
@click.option(
    '-i', '--backup-ext',
    metavar='EXT',
    help="Extension for backup file [default: ~]",
)
@click.option(
    '-c', '--create',
    is_flag=True,
    help="Treat nonexistent FILE as empty",
)
@click.option(
    '-m/-M', '--match-first/--match-last',
    default=False,
    help="`--regexp` replaces first/last matching line in input [default: last]",
)
@click.option(
    '-o', '--outfile',
    type=click.File("w"),
    help="Write output to given file",
)
@click.argument('line')
@click.argument(
    'file',
    type=click.Path(dir_okay=False, writable=True, allow_dash=True),
    default="-",
)
def add(
    line: str,
    file: str,
    regexp: Optional[str],
    backrefs: bool,
    backup: Optional[BackupWhen],
    backup_ext: Optional[str],
    create: bool,
    match_first: bool,
    inserter: Optional["Inserter"] = None,
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
    if file == "-" or outfile is not None:
        if file == "-":
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
        with click.open_file(file) as fp:
            before = fp.read()
        after = add_line_to_string(
            before,
            line,
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
        print(after, end='', file=outfp)
    else:
        add_line_to_file(
            file,
            line,
            regexp=regexp,
            inserter=inserter,
            match_first=match_first,
            backrefs=backrefs,
            backup=backup,
            backup_ext=backup_ext,
            create=create,
        )

@main.command()
@click.option(
    '--backup', '--backup-changed', 'backup',
    flag_value=CHANGED,
    help="Backup file if modified",
)
@click.option(
    '--backup-always', 'backup',
    flag_value=ALWAYS,
    help="Backup file whether modified or not"
)
@click.option(
    '-i', '--backup-ext',
    metavar='EXT',
    help="Extension for backup file [default: ~]",
)
@click.option(
    '-o', '--outfile',
    type=click.File("w"),
    help="Write output to given file",
)
@click.argument('regexp')
@click.argument(
    'file',
    type=click.Path(dir_okay=False, writable=True, allow_dash=True),
    default="-",
)
def remove(
    regexp: str,
    file: str,
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
    if file == "-" or outfile is not None:
        if file == "-":
            errmsg = "{option} cannot be set when reading from standard input."
        else:
            errmsg = "{option} is incompatible with --outfile."
        if backup_ext is not None:
            raise click.UsageError(errmsg.format(option="--backup-ext"))
        if backup is CHANGED:
            raise click.UsageError(errmsg.format(option="--backup-changed"))
        if backup is ALWAYS:
            raise click.UsageError(errmsg.format(option="--backup-always"))
        with click.open_file(file) as fp:
            before = fp.read()
        after = remove_lines_from_string(before, regexp)
        if outfile is None:
            outfp = click.get_text_stream("stdout")
        else:
            outfp = outfile
        # Don't use click.echo(), as it modifies ANSI sequences on Windows
        print(after, end='', file=outfp)
    else:
        remove_lines_from_file(
            file,
            regexp,
            backup=backup,
            backup_ext=backup_ext,
        )

if __name__ == '__main__':
    main()  # pragma: no cover
