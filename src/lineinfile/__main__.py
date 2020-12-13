from   typing import Any, Optional, TYPE_CHECKING, TextIO
import click
from   .      import (
    ALWAYS, AfterFirst, AfterLast, AtBOF, AtEOF, BackupWhen, BeforeFirst,
    BeforeLast, CHANGED, __version__, add_line_to_file, add_line_to_string,
    remove_lines_from_file, remove_lines_from_string,
)

if TYPE_CHECKING:
    from . import Locator

def set_locator(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    if value is not None:
        ctx.params["locator"] = value
    return value

@click.group()
@click.version_option(
    __version__,
    '-V', '--version',
    message='lineinfile %(version)s',
)
def main() -> None:
    pass

@main.command()
@click.option(
    '-a', '--after-first',
    metavar='REGEX',
    type=AfterFirst,
    callback=set_locator,
    expose_value=False,
)
@click.option(
    '-A', '--after-last',
    metavar='REGEX',
    type=AfterLast,
    callback=set_locator,
    expose_value=False,
)
@click.option(
    '-b', '--before-first',
    metavar='REGEX',
    type=BeforeFirst,
    callback=set_locator,
    expose_value=False,
)
@click.option(
    '-B', '--before-last',
    metavar='REGEX',
    type=BeforeLast,
    callback=set_locator,
    expose_value=False,
)
@click.option(
    '--bof',
    flag_value=AtBOF(),
    callback=set_locator,
    expose_value=False,
)
@click.option(
    '--eof',
    flag_value=AtEOF(),
    callback=set_locator,
    expose_value=False,
)
@click.option('-e', '--regexp', metavar='REGEX')
@click.option('--backrefs', is_flag=True)
@click.option('--backup', '--backup-changed', 'backup', flag_value=CHANGED)
@click.option('--backup-always', 'backup', flag_value=ALWAYS)
@click.option('-i', '--backup-ext', metavar='EXT')
@click.option('-c', '--create', is_flag=True)
@click.option('-m/-M', '--match-first/--match-last', default=False)
@click.option('-o', '--outfile', type=click.File("w"))
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
    locator: Optional["Locator"] = None,
    outfile: Optional[TextIO] = None,
) -> None:
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
            locator=locator,
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
            locator=locator,
            match_first=match_first,
            backrefs=backrefs,
            backup=backup,
            backup_ext=backup_ext,
            create=create,
        )

@main.command()
@click.option('--backup', '--backup-changed', 'backup', flag_value=CHANGED)
@click.option('--backup-always', 'backup', flag_value=ALWAYS)
@click.option('-i', '--backup-ext', metavar='EXT')
#@click.option('-c', '--create', is_flag=True)
@click.option('-o', '--outfile', type=click.File("w"))
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
    #create: bool,
    outfile: Optional[TextIO] = None,
) -> None:
    if backup_ext is not None and backup is None:
        backup = CHANGED
    if backup_ext == "":
        raise click.UsageError("--backup-ext cannot be empty")
    if file == "-" or outfile is not None:
        if backup_ext is not None:
            raise click.UsageError(
                "--backup-ext cannot be set when reading from standard input."
            )
        if backup is CHANGED:
            raise click.UsageError(
                "--backup-changed cannot be set when reading from standard input."
            )
        if backup is ALWAYS:
            raise click.UsageError(
                "--backup-always cannot be set when reading from standard input."
            )
        #if create:
        #    raise click.UsageError(
        #        "--create cannot be set when reading from standard input."
        #    )
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
            #create=create,
        )

if __name__ == '__main__':
    main()  # pragma: no cover
