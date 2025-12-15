from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Protocol
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
    Inserter,
    __version__,
    add_line_to_file,
    add_line_to_string,
    remove_lines_from_file,
    remove_lines_from_string,
    unescape,
)


class Subcommand(Protocol):
    def run(self) -> int: ...


@dataclass
class Command:
    subcommand: Subcommand

    @classmethod
    def from_args(cls, argv: list[str] | None = None) -> Command:
        parser = argparse.ArgumentParser(
            description=(
                "Add & remove lines in files by regex\n"
                "\n"
                "Visit <https://github.com/jwodder/lineinfile> for more information.\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "-V", "--version", action="version", version=f"%(prog)s {__version__}"
        )

        subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        addparser = subparsers.add_parser(
            "add",
            help="Add LINE to FILE if it's not already present.",
            description=(
                "If a Python regular expression is given with the `-e`/`--regexp`\n"
                "option and it matches any lines in the file, LINE will replace the last\n"
                "matching line (or the first matching line, if `--match-first` is given).\n"
                "If the regular expression does not match any lines (or no regular\n"
                "expression is specified) and LINE is not found in the file, the line is\n"
                "inserted at the end of the file by default; this can be changed with the\n"
                "`--after-first`, `--after-last`, `--before-first`, `--before-last`,\n"
                "and `--bof` options.\n"
                "\n"
                "If no file name is given on the command line, input is read from standard\n"
                "input, and the result is written to standard output.  It is an error to\n"
                "specify any of the `--backup-changed`, `--backup-always`, `--backup-ext`,\n"
                "or `--create` options when no file is given.\n"
            ),
        )

        addparser.add_argument(
            "-a",
            "--after-first",
            metavar="REGEX",
            type=AfterFirst,
            dest="inserter",
            help="Insert LINE after the first line matching REGEX",
        )
        addparser.add_argument(
            "-A",
            "--after-last",
            metavar="REGEX",
            type=AfterLast,
            dest="inserter",
            help="Insert LINE after the last line matching REGEX",
        )
        addparser.add_argument(
            "-b",
            "--before-first",
            metavar="REGEX",
            type=BeforeFirst,
            dest="inserter",
            help="Insert LINE before the first line matching REGEX",
        )
        addparser.add_argument(
            "-B",
            "--before-last",
            metavar="REGEX",
            type=BeforeLast,
            dest="inserter",
            help="Insert LINE before the last line matching REGEX",
        )
        addparser.add_argument(
            "--bof",
            action="store_const",
            const=AtBOF(),
            dest="inserter",
            help="Insert LINE at the beginning of the file",
        )
        addparser.add_argument(
            "--eof",
            action="store_const",
            const=AtEOF(),
            dest="inserter",
            help="Insert LINE at the end of the file [default]",
        )
        addparser.add_argument(
            "-e",
            "--regexp",
            metavar="REGEX",
            help="Replace the last line matching REGEX with LINE",
        )
        addparser.add_argument(
            "--backrefs",
            action="store_true",
            help="Use `--regexp` match to expand capturing groups in LINE",
        )
        addparser.add_argument(
            "--backup",
            "--backup-changed",
            action="store_const",
            const=CHANGED,
            dest="backup",
            help="Backup file if modified",
        )
        addparser.add_argument(
            "--backup-always",
            action="store_const",
            const=ALWAYS,
            dest="backup",
            help="Backup file whether modified or not",
        )
        addparser.add_argument(
            "-i",
            "--backup-ext",
            metavar="EXT",
            help="Extension for backup file [default: ~]",
        )
        addparser.add_argument(
            "-c",
            "--create",
            action="store_true",
            help="Treat nonexistent FILE as empty",
        )
        addparser.add_argument(
            "-L",
            "--line",
            dest="line_opt",
            metavar="LINE",
            help="Use LINE as the line to insert",
        )
        addparser.add_argument(
            "-m",
            "--match-first",
            action="store_true",
            dest="match_first",
            help="`--regexp` replaces first matching line in input",
        )
        addparser.add_argument(
            "-M",
            "--match-last",
            action="store_false",
            dest="match_first",
            help="`--regexp` replaces last matching line in input [default]",
        )
        addparser.add_argument(
            "-o", "--outfile", metavar="FILE", help="Write output to given file"
        )
        addparser.add_argument("line", nargs="?")
        addparser.add_argument("file", nargs="?")

        removeparser = subparsers.add_parser(
            "remove",
            help="Delete all lines from FILE that match REGEXP",
            description=(
                "If no file name is given on the command line, input is read from standard\n"
                "input, and the result is written to standard output.  It is an error to\n"
                "specify any of the `--backup-changed`, `--backup-always`, or `--backup-ext`\n"
                "options when no file is given.\n"
            ),
        )

        removeparser.add_argument(
            "--backup",
            "--backup-changed",
            action="store_const",
            const=CHANGED,
            dest="backup",
            help="Backup file if modified",
        )
        removeparser.add_argument(
            "--backup-always",
            action="store_const",
            const=ALWAYS,
            dest="backup",
            help="Backup file whether modified or not",
        )
        removeparser.add_argument(
            "-i",
            "--backup-ext",
            metavar="EXT",
            help="Extension for backup file [default: ~]",
        )
        removeparser.add_argument(
            "-e",
            "--regexp",
            metavar="REGEX",
            dest="regexp_opt",
            help="Replace the last line matching REGEX with LINE",
        )
        removeparser.add_argument(
            "-o", "--outfile", metavar="FILE", help="Write output to given file"
        )
        removeparser.add_argument("regexp", nargs="?")
        removeparser.add_argument("file", nargs="?")

        args = parser.parse_args(argv)
        subcommand: Subcommand
        match args.subcommand:
            case "add":
                subcommand = AddCommand(
                    line=args.line,
                    file=args.file,
                    line_opt=args.line_opt,
                    regexp=args.regexp,
                    backrefs=args.backrefs,
                    backup=args.backup,
                    backup_ext=args.backup_ext,
                    create=args.create,
                    match_first=args.match_first,
                    inserter=args.inserter,
                    outfile=args.outfile,
                )
            case "remove":
                subcommand = RemoveCommand(
                    regexp=args.regexp,
                    file=args.file,
                    regexp_opt=args.regexp_opt,
                    backup=args.backup,
                    backup_ext=args.backup_ext,
                    outfile=args.outfile,
                )
            case cmd:  # pragma: no cover
                raise AssertionError(f"Unexpected subcommand: {cmd!r}")
        return Command(subcommand=subcommand)

    def run(self) -> int:
        try:
            return self.subcommand.run()
        except Exception as e:
            print(f"lineinfile: {e}", file=sys.stderr)
            return 1


@dataclass
class AddCommand:
    line: str | None
    file: str | None
    line_opt: str | None
    regexp: str | None
    backrefs: bool
    backup: BackupWhen | None
    backup_ext: str | None
    create: bool
    match_first: bool
    inserter: Inserter | None
    outfile: str | None

    def run(self) -> int:
        backup: BackupWhen | None
        if self.backup_ext is not None and self.backup is None:
            backup = CHANGED
        else:
            backup = self.backup
        if self.backrefs and self.regexp is None:
            raise ValueError("--backrefs cannot be specified without --regexp")
        if self.backup_ext == "":
            raise ValueError("--backup-ext cannot be empty")
        if self.line_opt is None:
            if self.line is None:
                raise ValueError("No LINE given")
            else:
                theline = self.line
            thefile = "-" if self.file is None else self.file
        else:
            theline = self.line_opt
            thefile = "-" if self.line is None else self.line
            if self.file is not None:
                raise ValueError("-L/--line given with too many positional arguments")
        if not self.backrefs:
            theline = unescape(theline)
        if thefile == "-" or self.outfile is not None:
            if thefile == "-":
                errmsg = "{option} cannot be set when reading from standard input."
            else:
                errmsg = "{option} is incompatible with --outfile."
            if self.backup_ext is not None:
                raise ValueError(errmsg.format(option="--backup-ext"))
            if backup is CHANGED:
                raise ValueError(errmsg.format(option="--backup-changed"))
            if backup is ALWAYS:
                raise ValueError(errmsg.format(option="--backup-always"))
            if self.create:
                raise ValueError(errmsg.format(option="--create"))
            if thefile == "-":
                before = sys.stdin.read()
            else:
                before = Path(thefile).read_text(encoding="utf-8")
            after = add_line_to_string(
                before,
                theline,
                regexp=self.regexp,
                inserter=self.inserter,
                match_first=self.match_first,
                backrefs=self.backrefs,
            )
            if self.outfile is None or self.outfile == "-":
                print(after, end="")
            else:
                Path(self.outfile).write_text(after, encoding="utf-8")
        else:
            add_line_to_file(
                thefile,
                theline,
                regexp=self.regexp,
                inserter=self.inserter,
                match_first=self.match_first,
                backrefs=self.backrefs,
                backup=backup,
                backup_ext=self.backup_ext,
                create=self.create,
                encoding="utf-8",
            )
        return 0


@dataclass
class RemoveCommand:
    regexp: str | None
    file: str | None
    regexp_opt: str | None
    backup: BackupWhen | None
    backup_ext: str | None
    outfile: str | None

    def run(self) -> int:
        backup: BackupWhen | None
        if self.backup_ext is not None and self.backup is None:
            backup = CHANGED
        else:
            backup = self.backup
        if self.backup_ext == "":
            raise ValueError("--backup-ext cannot be empty")
        if self.regexp_opt is None:
            if self.regexp is None:
                raise ValueError("No REGEXP given")
            else:
                theregexp = self.regexp
            thefile = "-" if self.file is None else self.file
        else:
            theregexp = self.regexp_opt
            thefile = "-" if self.regexp is None else self.regexp
            if self.file is not None:
                raise ValueError("-e/--regexp given with too many positional arguments")
        if thefile == "-" or self.outfile is not None:
            if thefile == "-":
                errmsg = "{option} cannot be set when reading from standard input."
            else:
                errmsg = "{option} is incompatible with --outfile."
            if self.backup_ext is not None:
                raise ValueError(errmsg.format(option="--backup-ext"))
            if backup is CHANGED:
                raise ValueError(errmsg.format(option="--backup-changed"))
            if backup is ALWAYS:
                raise ValueError(errmsg.format(option="--backup-always"))
            if thefile == "-":
                before = sys.stdin.read()
            else:
                before = Path(thefile).read_text(encoding="utf-8")
            after = remove_lines_from_string(before, theregexp)
            if self.outfile is None or self.outfile == "-":
                print(after, end="")
            else:
                Path(self.outfile).write_text(after, encoding="utf-8")
        else:
            remove_lines_from_file(
                thefile,
                theregexp,
                backup=backup,
                backup_ext=self.backup_ext,
                encoding="utf-8",
            )
        return 0


def main(argv: list[str] | None = None) -> int:
    return Command.from_args(argv).run()


if __name__ == "__main__":
    main()  # pragma: no cover
