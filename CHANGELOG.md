v0.5.0 (2025-12-15)
-------------------
- Support Python 3.14
- Drop support for Python 3.8 and 3.9
- Drop `click` dependency
    - As a consequence, CLI arguments of the form `-e REGEX` where `REGEX`
      begins with a hyphen must now be written as `--regexp=REGEX`.

v0.4.2 (2025-08-02)
-------------------
- Exclude click v8.2.2 from dependencies due to breakage caused by
  https://github.com/pallets/click/issues/3024

v0.4.1 (2024-12-01)
-------------------
- Support Python 3.10, 3.11, 3.12, and 3.13
- Drop support for Python 3.6 and 3.7
- The CLI now always opens files in UTF-8
- Add type annotations to tests
- Migrated from setuptools to hatch

v0.4.0 (2021-05-12)
-------------------
- Paths passed to `add_line_to_file()` and `remove_lines_from_file()` can now
  be `bytes` or `os.PathLike[bytes]`
- Support Click 8

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
