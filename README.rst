.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.

.. image:: https://github.com/jwodder/lineinfile/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/lineinfile/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/lineinfile/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/lineinfile

.. image:: https://img.shields.io/pypi/pyversions/lineinfile.svg
    :target: https://pypi.org/project/lineinfile/

.. image:: https://img.shields.io/github/license/jwodder/lineinfile.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/lineinfile>`_
| `PyPI <https://pypi.org/project/lineinfile/>`_
| `Issues <https://github.com/jwodder/lineinfile/issues>`_

Inspired by (but not affiliated with) `the Ansible module of the same name`__,
``lineinfile`` provides a command and library for adding a line to a file if
it's not already there and for removing lines matching a pattern from a file.
There are options for using a regex to find a line to update or to determine
which line to insert before or after.  There are options for backing up the
modified file with a custom file extension and for treating a nonexistent file
as though it's just empty.  There's even an option for determining the line to
insert based on capturing groups in the matching regex.

__ https://docs.ansible.com/ansible/latest/collections/ansible/builtin/
   lineinfile_module.html

Unlike the Ansible module, this package does not perform any management of file
attributes; those must be set externally.


Installation
============
``lineinfile`` requires Python 3.6 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install
``lineinfile`` and its dependencies::

    python3 -m pip install lineinfile


Examples
========

A crude ``.ini``-file updater: Set ``theoption`` to ``value``, and if no
setting for ``theoption`` is found in the file, add one after the line
"``[thesection]``":

.. code:: console

    $ lineinfile add \
        --after-first "^\[thesection\]$" \
        -e "^theoption\s*=" \
        "theoption = thevalue" \
        settings.ini

The equivalent operation in Python:

.. code:: python

    from lineinfile import AfterFirst, add_line_to_file

    add_line_to_file(
        "settings.ini",
        "theoption = thevalue",
        regexp=r"^theoption\s*=",
        inserter=AfterFirst(r"^\[thesection\]$"),
    )

Replace the first instance of "``foo = ...``" with "``foo = 'bar'``",
preserving indentation, and create a backup of the file with the extension
``.bak``, even if no changes were made:

.. code:: console

    $ lineinfile add \
        -e "^(\s*)foo\s*=" \
        --backrefs \
        --match-first \
        --backup-always -i.bak \
        "\1foo = 'bar'" \
        file.py

The equivalent operation in Python:

.. code:: python

    from lineinfile import ALWAYS, add_line_to_file

    add_line_to_file(
        "file.py",
        r"\1foo = 'bar'",
        regexp=r"^(\s*)foo\s*=",
        backrefs=True,
        match_first=True,
        backup=ALWAYS,
        backup_ext=".bak",
    )


Command-Line Usage
==================

The ``lineinfile`` command has two subcommands, ``add`` and ``remove``.

``add``
-------

::

    lineinfile add [<options>] <line> [<file>]

Add the given ``line`` to the file if it is not already present.  If a `Python
regular expression`_ is given with the ``-e``/``--regexp`` option and it matches
any lines in the file, ``line`` will replace the last matching line (or the
first matching line, if ``--match-first`` is given).  If the regular expression
does not match any lines (or no regular expression is specified) and ``line``
is not found in the file, the line is inserted at the end of the file by
default; this can be changed with the ``--after-first``, ``--after-last``,
``--before-first``, ``--before-last``, and ``--bof`` options.

If no file name is given on the command line, input is read from standard
input, and the result is written to standard output.  It is an error to specify
any of the ``--backup-changed``, ``--backup-always``, ``--backup-ext``, or
``--create`` options when no file is given.

.. _Python regular expression: https://docs.python.org/3/library/re.html
                               #regular-expression-syntax

Options
```````

-a REGEX, --after-first REGEX
                            If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` after the first line that
                            matches the regular expression ``REGEX``, or at the
                            end of the file if no line matches ``REGEX``.

-A REGEX, --after-last REGEX
                            If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` after the last line that
                            matches the regular expression ``REGEX``, or at the
                            end of the file if no line matches ``REGEX``.

-b REGEX, --before-first REGEX
                            If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` before the first line
                            that matches the regular expression ``REGEX``, or
                            at the end of the file if no line matches
                            ``REGEX``.

-B REGEX, --before-last REGEX
                            If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` before the last line that
                            matches the regular expression ``REGEX``, or at the
                            end of the file if no line matches ``REGEX``.

--bof                       If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` at the beginning of the
                            file.

--eof                       If neither ``line`` nor ``--regexp`` is found in
                            the file, insert ``line`` at the end of the file.
                            This is the default.

-e REGEX, --regexp REGEX    If the given regular expression matches any lines
                            in the file, replace the last matching line (or
                            first, if ``--match-first`` is given) with
                            ``line``.

--backrefs                  If ``--regexp`` matches, the capturing groups in
                            the regular expression are used to expand any
                            ``\n``, ``\g<n>``, or ``\g<name>`` backreferences
                            in ``line``, and the resulting string replaces the
                            matched line in the input.

                            If ``--regexp`` does not match, the input is left
                            unchanged.

                            It is an error to specify this option without
                            ``--regexp``.

--backup, --backup-changed  If the input file is modified, create a backup of
                            the original file.  The backup will have the
                            extension specified with ``--backup-ext`` (or ``~``
                            if no extension is specified) appended to its
                            filename.

--backup-always             Create a backup of the original file regardless of
                            whether or not it's modified.  The backup will have
                            the extension specified with ``--backup-ext`` (or
                            ``~`` if no extension is specified) appended to its
                            filename.

-i EXT, --backup-ext EXT    Create a backup of the input file with ``EXT``
                            added to the end of the filename.  Implies
                            ``--backup-changed`` if neither it nor
                            ``--backup-always`` is also given.

-c, --create                If the input file does not exist, pretend it's
                            empty instead of erroring, and create it with the
                            results of the operation.  No backup file will be
                            created for a nonexistent file, regardless of the
                            other options.

                            If the input file does not exist and no changes are
                            made (because ``--backrefs`` was specified and
                            ``--regexp`` didn't match), the file will not be
                            created.

-m, --match-first           If ``--regexp`` matches, replace the first matching
                            line with ``line``.

-M, --match-last            If ``--regexp`` matches, replace the last matching
                            line with ``line``.  This is the default.

-o FILE, --outfile FILE     Write the resulting file contents to ``FILE``
                            instead of modifying the input file.

                            It is an error to specify this option with any of
                            ``--backup-changed``, ``--backup-always``, or
                            ``--backup-ext``.


``remove``
----------

::

    lineinfile remove [<options>] <regexp> [<file>]

Delete all lines from the given file that match the given `Python regular
expression`_.

If no file name is given on the command line, input is read from standard
input, and the result is written to standard output.  It is an error to specify
any of the ``--backup-changed``, ``--backup-always``, or ``--backup-ext``
options when no file is given.

Options
```````

--backup, --backup-changed  If the input file is modified, create a backup of
                            the original file.  The backup will have the
                            extension specified with ``--backup-ext`` (or ``~``
                            if no extension is specified) appended to its
                            filename.

--backup-always             Create a backup of the original file regardless of
                            whether or not it's modified.  The backup will have
                            the extension specified with ``--backup-ext`` (or
                            ``~`` if no extension is specified) appended to its
                            filename.

-i EXT, --backup-ext EXT    Create a backup of the input file with ``EXT``
                            added to the end of the filename.  Implies
                            ``--backup-changed`` if neither it nor
                            ``--backup-always`` is also given.

-o FILE, --outfile FILE     Write the resulting file contents to ``FILE``
                            instead of modifying the input file.

                            It is an error to specify this option with any of
                            ``--backup-changed``, ``--backup-always``, or
                            ``--backup-ext``.


Library API
===========

Note that all regular expression matching is done with the ``Pattern.search()``
method, i.e., it is not anchored at the start of the line.  In order to force a
regular expression to start matching at the beginning of a line, prefix it with
``^`` or ``\A``.

.. code:: python

    lineinfile.add_line_to_file(
        filepath: Union[str, os.PathLike],
        line: str,
        regexp: Optional[Union[str, re.Pattern[str]]] = None,
        inserter: Optional[Inserter] = None,
        match_first: bool = False,
        backrefs: bool = False,
        backup: Optional[BackupWhen] = None,
        backup_ext: Optional[str] = None,
        create: bool = False,
    ) -> bool

Add the given ``line`` to the file at ``filepath`` if it is not already
present.  Returns ``True`` if the file is modified.  If ``regexp`` is set to a
regular expression (either a string or a compiled pattern object) and it
matches any lines in the file, ``line`` will replace the last matching line (or
the first matching line, if ``match_first=True``).  If the regular expression
does not match any lines (or no regular expression is specified) and ``line``
is not found in the file, the line is inserted at the end of the file by
default; this can be changed by passing the appropriate object as the
``inserter`` argument; see "Inserters_" below.

When ``backrefs`` is true, if ``regexp`` matches, the capturing groups in the
regular expression are used to expand any ``\n``, ``\g<n>``, or ``\g<name>``
backreferences in ``line``, and the resulting string replaces the matched line
in the input.  If ``backrefs`` is true and ``regexp`` does not match, the file
is left unchanged.  It is an error to set ``backrefs`` to true without also
setting ``regexp``.

When ``backup`` is set to ``lineinfile.CHANGED``, a backup of the file's
original contents is created if the file is modified.  When ``backup`` is set
to ``lineinfile.ALWAYS``, a backup is always created, regardless of whether the
file is modified.  The name of the backup file will be the same as the
original, with the value of ``backup_ext`` (default: ``~``) appended.

If ``create`` is true and ``filepath`` does not exist, pretend it's empty
instead of erroring, and create it with the results of the operation.  No
backup file will ever be created for a nonexistent file.  If ``filepath`` does
not exist and no changes are made (because ``backrefs`` was set and ``regexp``
didn't match), the file will not be created.


.. code:: python

    lineinfile.remove_lines_from_file(
        filepath: Union[str, os.PathLike],
        regexp: Union[str, re.Pattern[str]],
        backup: Optional[BackupWhen] = None,
        backup_ext: Optional[str] = None,
    ) -> bool

Delete all lines from the file at ``filepath`` that match the regular
expression ``regexp`` (either a string or a compiled pattern object).  Returns
``True`` if the file is modified.

When ``backup`` is set to ``lineinfile.CHANGED``, a backup of the file's
original contents is created if the file is modified.  When ``backup`` is set
to ``lineinfile.ALWAYS``, a backup is always created, regardless of whether the
file is modified.  The name of the backup file will be the same as the
original, with the value of ``backup_ext`` (default: ``~``) appended.


.. code:: python

    lineinfile.add_line_to_string(
        s: str,
        line: str,
        regexp: Optional[Union[str, re.Pattern[str]]] = None,
        inserter: Optional[Inserter] = None,
        match_first: bool = False,
        backrefs: bool = False,
    ) -> str

Add the given ``line`` to the string ``s`` if it is not already present and
return the result.  If ``regexp`` is set to a regular expression (either a
string or a compiled pattern object) and it matches any lines in the input,
``line`` will replace the last matching line (or the first matching line, if
``match_first=True``).  If the regular expression does not match any lines (or
no regular expression is specified) and ``line`` is not found in the input, the
line is inserted at the end of the input by default; this can be changed by
passing the appropriate object as the ``inserter`` argument; see "Inserters_"
below.

When ``backrefs`` is true, if ``regexp`` matches, the capturing groups in the
regular expression are used to expand any ``\n``, ``\g<n>``, or ``\g<name>``
backreferences in ``line``, and the resulting string replaces the matched line
in the input.  If ``backrefs`` is true and ``regexp`` does not match, the input
is left unchanged.  It is an error to set ``backrefs`` to true without also
setting ``regexp``.


.. code:: python

    lineinfile.remove_lines_from_string(
        s: str,
        regexp: Union[str, re.Pattern[str]],
    ) -> str

Delete all lines from the string ``s`` that match the regular expression
``regexp`` (either a string or a compiled pattern object) and return the
result.


Inserters
---------

Inserters are objects used by the ``add_line_*`` functions to determine the
location at which to insert ``line`` when it is not found in the input and the
``regexp`` argument, if set, doesn't match any lines.

``lineinfile`` provides the following inserter classes:

``AtBOF()``
    Always inserts the line at the beginning of the file

``AtEOF()``
    Always inserts the line at the end of the file

``AfterFirst(regexp)``
    Inserts the line after the first input line that matches the given regular
    expression (either a string or a compiled pattern object), or at the end of
    the file if no line matches.

``AfterLast(regexp)``
    Inserts the line after the last input line that matches the given regular
    expression (either a string or a compiled pattern object), or at the end of
    the file if no line matches.

``BeforeFirst(regexp)``
    Inserts the line before the first input line that matches the given regular
    expression (either a string or a compiled pattern object), or at the end of
    the file if no line matches.

``BeforeLast(regexp)``
    Inserts the line before the last input line that matches the given regular
    expression (either a string or a compiled pattern object), or at the end of
    the file if no line matches.


Handling of Line Endings
========================

``lineinfile`` operates on files using Python's universal newlines mode, in
which all LF (``\n``), CR LF (``\r\n``), and CR (``\r``) sequences in a file
are converted to just LF when read into a Python string, and LF is in turn
converted to the operating system's native line separator when written back to
disk.

In the majority of cases, this allows you to use ``$`` in regular expressions
and have it always match the end of an input line, regardless of what line
ending the line had on disk.  However, when using ``add_line_to_string()`` or
``remove_lines_from_string()`` with a string with non-LF line separators,
things can get tricky.  ``lineinfile`` follows the following rules regarding
line separators:

- Lines are terminated by LF, CR, and CR LF only.

- When an ``add_line_*`` function compares a ``line`` argument against a line
  in the input, the line ending is stripped from both lines.  This is a
  deviation from Ansible's behavior, where only the input line is stripped.

- When matching an input line against ``regexp`` or an inserter, line endings
  are not stripped.  Note that a regex like ``r"foo$"`` will not match a line
  that ends with a non-LF line ending, so this can result in patterns not
  matching where you might naïvely expect them to match.

- When adding a line to the end of a file, if the file does not end with a line
  ending already, an LF is appended before adding the line.

- When adding ``line`` to a document (either as a new line or replacing a
  pre-existing line), LF is appended to the line if it does not already end
  with a line separator; any line ending on the line being replaced (if any) is
  ignored (If you want to preserve it, use backrefs).  If the only difference
  between the resulting ``line`` and the line it's replacing is the line
  ending, the replacement still occurs, the line ending is modified, and the
  document is changed.
