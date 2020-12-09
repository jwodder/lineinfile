from   typing import Any, Optional, TYPE_CHECKING
import click
from   .      import (
    ALWAYS, AfterFirst, AfterLast, AtBOF, AtEOF, BackupWhen, BeforeFirst,
    BeforeLast, CHANGED, __version__, add_line_to_file,
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
@click.argument('line')
@click.argument('file', type=click.Path(dir_okay=False, writable=True))
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
) -> None:
    if backup_ext is not None and backup is None:
        backup = CHANGED
    if backrefs and regexp is None:
        raise click.UsageError("--backrefs cannot be specified without --regexp")
    if backup_ext == "":
        raise click.UsageError("--backup-ext cannot be empty")
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

if __name__ == '__main__':
    main()  # pragma: no cover
