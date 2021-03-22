v0.4.0 (in development)
-----------------------
- Paths passed to `add_line_to_file()` and `remove_lines_from_file()` can now
  be `bytes` or `os.PathLike[bytes]`

v0.3.0 (2020-12-27)
-------------------
- Gave the `add_line_to_file()` and `remove_lines_from_file()` functions
  `encoding` and `errors` arguments
- Inserter instances can now be safely reused across multiple calls to
  `add_line_to_string()`/`add_line_to_file()`

v0.2.0 (2020-12-21)
-------------------
- The `add` command now expands backslash escapes in `line`.
- Gave `add` an `-L/--line` option for specifying the `line`, especially when
  it begins with a hyphen.
- Gave `remove` an `-e/--regexp` option for specifying the `regexp`, especially
  when it begins with a hyphen.

v0.1.0 (2020-12-17)
-------------------
Initial release
