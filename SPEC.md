Write a Python command & library based on the Ansible module of the same name

- <https://docs.ansible.com/ansible/latest/collections/ansible/builtin/lineinfile_module.html>
- <https://github.com/ansible/ansible/blob/devel/lib/ansible/modules/lineinfile.py>

- Commands:
    - `lineinfile add [<options>] <line> [<file>]`
        - Options:
            - Each one of the following overrides all previous occurrences from
              the same set:
                - -a, --after-first REGEX
                - -A, --after-last REGEX
                - -b, --before-first REGEX
                - -B, --before-last REGEX
                - --eof (default)
                - --bof
            - -e, --regexp REGEX
            - -i, --backup-ext EXTENSION
                - Implies `--backup-changed` if backup mode is not otherwise
                  set
            - --backup, --backup-changed — back up file if changed
            - --backup-always — causes file to be backed up even if not changed
            - --backrefs
                - Error if `--regexp` is not also given
            - -c, --create — Treat missing files as empty
                - TODO: Should this create the file even if there are no
                  changes?
            - -m, --match-first — causes the first line matching the regexp to
              be replaced
            - -M, --match-last — causes the last line matching the regexp to be
              replaced; default
            - -o, --outfile — incompatible with backup options
            - Add an `-L <line>` option for specifying the line in case it
              begins with a hyphen.
    - `lineinfile remove [<options>] <regexp> [<file>]`
        - Options:
            - [backup options from `add`]
            - -F, --fixed-string — treat regex as a fixed string
            - -o, --outfile — incompatible with backup options
        - It should be possible to specify the regexp with `-e <regexp>` in
          case it begins with a hyphen.
        - Should this have a `--create` option or not?  If so, then shouldn't
          `add --create` create an empty file even if there are no changes?

- Library functions:
    - `add_line_to_file(filepath, line, regexp=None, locator=None, backrefs=False, match_first=False, backup=None, backup_ext='~', create=False) -> bool`
        - Returns true iff file changed
        - `backup` takes the following values:
            - `None` — no backup
            - `lineinfile.CHANGED` — backup on change
            - `lineinfile.ALWAYS` — always backup

            The constants are values of a `BackupWhen` enum that are copied
            into the global scope.

    - `remove_lines_from_file(filepath, regexp, [backup options]) -> bool`
        - Returns true iff file changed
    - `add_line_to_string(s, line, regexp=None, locator=None, backrefs=False, match_first=False) -> str`
    - `remove_lines_from_string(s, regexp) -> str`

- There are six locator classes:
    - `AtBOF()`
    - `AtEOF()`
    - `AfterFirst(str_or_regex)`
    - `AfterLast(str_or_regex)`
    - `BeforeFirst(str_or_regex)`
    - `BeforeLast(str_or_regex)`

- The default locator is `AtEOF()`

- Locators have a `feed(int, str) -> None` method that is passed each line
  number & line of the file one at a time.  Once the file is processed, the
  `get_index() -> Optional[int]` method is called to retrieve the index to pass
  to `list_of_lines.insert()` for adding the new line.
    - A return value of `None` from `get_index()` means to insert the line at
      the end of the file.

- Notes on the Ansible module's behavior:
    - Adding a line: When a `regexp` is given, first the file is searched for
      any matching lines, and if none are found, the file is searched for lines
      that equal `line` (after stripping line endings).
    - Removing a line:
        - When a `regexp` is given, all lines matching it are removed, and
          `line` is ignored.
        - When no `regexp` is given, all lines equaling `line` (after stripping
          line endings) are removed.

- TODO: Give the "add" operations an option for causing all pre-existing lines
  matching the regex/line to be deleted before replacing
    - `--remove-extra-matches`? `--remove-other-matches`?
    - `-u`, `--unique`? `--unique-match`?

- Give the CLI an option for using the `regex` library? (Installed as an extra)
    - `--use-regex`?

- Give `add` a `--fixed-string` option for modifying `-e` and/or `-aAbB`?
- Give the commands `-x`/`--line-regexp` options for causing regexes/fixed
  strings to be compared for full-line matches?

- Should there be library functions that operate on a list of pre-split lines?
    - Such functions should not do anything special regarding line endings

- CLI: When `--backrefs` is not given, should escape sequences in the line be
  expanded?

- Should the library functions return structures containing information on
  what, if anything, was changed?

- idea: When `backrefs` is in effect, support passing the string to expand
  separately from the `line` (Pass it as the `backrefs` value?) so that a line
  can still be added even if the regexp doesn't match

- Add encoding & errors options for the file functions?

- Give the CLI an `--exit-code` option for altering the exit code based on
  whether anything changed?  (Failure on change?)


Rules for Handling Line Endings
-------------------------------
- Lines are terminated by LF, CR, and CR LF only.
- When comparing an input line against a `line` argument, the line ending is
  stripped from both.
    - This is a deviation from Ansible's behavior, which only strips the input
      line.
- When matching an input line against `regexp` or a locator, line endings are
  not stripped.
- When adding a line to the end of a file, if the file does not end with a line
  ending, a `\n` is appended before adding `line`.
- When adding `line` to a document (either as a new line or replacing a
  pre-existing line), `\n` (converted to the OS's line separator when working
  with a file) is appended to the line if it does not already end with a line
  separator; any line ending on the line being replaced (if any) is ignored
  (If you want to preserve it, use backrefs).  If the only difference between
  the resulting `line` and the line it's replacing is the line ending, the
  replacement still occurs, the line ending is modified, and the document is
  changed.
