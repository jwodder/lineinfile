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
            - -e, --regexp REGEX
            - -x, --ext EXTENSION — causes file to be backed up if changed
                - Rethink name
            - --always-backup — causes file to be backed up even if not changed
                - If --ext is not also given, backup extension defaults to `~`
                - Rename to "--force-backup"?
            - --backrefs
                - Error if `--regexp` is not also given
            - -c, --create — Treat missing files as empty
            - -m, --match-first — causes the first line matching the regexp to
              be replaced
            - -M, --match-last — causes the last line matching the regexp to be
              replaced; default
            - -o, --outfile — incompatible with backup options
    - `lineinfile remove [<options>] <regexp> [<file>]`
        - Options:
            - [backup options from `add`]
            - -F, --fixed-string — treat regex as a fixed string
            - -o, --outfile — incompatible with backup options

- Library functions:
    - `add_line_to_file(filepath, line, regexp=None, locator=None, backrefs=False, match_first=False, backup_ext=None, always_backup=False, create=False) -> bool`
        - Returns true iff file changed
    - `remove_lines_from_file(filepath, regexp, [backup options]) -> bool`
        - Returns true iff file changed
    - `add_line_to_string(s, line, regexp=None, locator=None, backrefs=False, match_first=False) -> str`
    - `remove_lines_from_string(s, regexp) -> str`

- There are four locator classes:
    - `AtBOF()`
    - `AtEOF()`
    - `AfterFirst(str_or_regex)`
    - `AfterLast(str_or_regex)`
    - `BeforeFirst(str_or_regex)`
    - `BeforeLast(str_or_regex)`

- The default locator is `AtEOF()`

- Locators have a `feed(str) -> None` method that is passed each line of the
  file one at a time.  Once the file is processed, the `get_index() -> int`
  method is called to retrieve the index to pass to `list_of_lines.insert()`
  for adding the new line.

- TODO: Look into exactly how `regexp` vs. no `regexp` affects behavior with
  `state` being both `present` and `absent`

- Notes on the Ansible module's behavior:
    - Adding a line: When a `regexp` is given, first the file is searched for
      any matching lines, and if none are found, the file is searched for lines
      that equal `line` (after stripping line endings).
    - Removing a line:
        - When a `regexp` is given, all lines matching it are removed, and
          `line` is ignored.
        - When no `regexp` is given, all lines equaling `line` (after stripping
          line endings) are removed.
    - `BOF` has a special meaning to both `insertbefore` and `insertafter`, but
      `EOF` only has a special meaning to `insertafter`.
        - Don't copy this behavior

- TODO: Give the "add" operations an option for causing all pre-existing lines
  matching the regex/line to be deleted before replacing
    - `--remove-extra-matches`?
    - `-u`, `--unique`? `--unique-match`?

- Give the CLI an option for using the `regex` library? (Installed as an extra)
    - `--use-regex`?


Test Cases
----------
- Adding a line that does/doesn't end with `\n`
- Invoking the CLI with different combinations of `-aAbB`
- `--create` + nonexistent file + `--ext`/`--always-backup` → no backup
  created?
- Specifying `EOF`/`BOF`/`[E]OF`/`[B]OF` on the command line
- Passing `EOF` to a `--before-*` option → treated as a regex
- Passing `BOF` to an `--after-*` option → treated as a regex
- function for modifying a file, CLI: line is replaced with itself → no change,
  no backup
- `line` argument has a line ending (Strip it?)
- regex with `$` anchor and input line has a non-`\n` line ending
