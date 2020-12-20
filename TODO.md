- General CLI:
    - Add an option for using the `regex` library? (Installed as an extra)
        - `--use-regex`?
    - Add an `--exit-code` option for altering the exit code based on whether
      anything changed?  (Failure on change?)

- `add` command:
    - Add an `-F`, `--fixed-string` option for treating the regexp (and also
      `-aAbB`?) as a fixed string
    - Add an `-x`, `--line-regexp` option for causing the regexp (and also
      `-aAbB`?) to be compared for full-line matches?

- `remove` command:
    - Add an `-e <regexp>` option for specifying the regexp in case it begins
      with a hyphen.
    - Add an `-F`, `--fixed-string` option for treating the regexp as a fixed
      string
    - Add an `-x`, `--line-regexp` option for causing the regexp to be compared
      for full-line matches?

- Library:
    - Add encoding & errors options for the file functions
    - Make inserters not contain mutable state, so that they are reusable
      across `add_line_*` calls
    - Add functions that operate on lists of pre-split lines?
        - Such functions should not do anything special regarding line endings
    - Should the library functions return structures containing information on
      what, if anything, was changed, the path to the backup, etc.?

- Give the "add" operations an option for causing all pre-existing lines
  matching the regex/line to be deleted before replacing
    - `--remove-extra-matches`? `--remove-other-matches`?
    - `-u`, `--unique`? `--unique-match`?

- idea: When `backrefs` is in effect, support passing the string to expand
  separately from the `line` (Pass it as the `backrefs` value?) so that a line
  can still be added even if the regexp doesn't match

- Get full coverage
