# FAQ

## What pystrip will not remove

Docstring detection is syntax-based, not text-based. pystrip does not guess
intent from quote style or wording; it removes a literal string expression only
when it sits in the docstring position.

- **String literals that are not docstrings.** A string counts as a docstring
  only when it is the first statement in a module, class, or function body.
- **Strings that merely look like comments**, such as `"value # not a comment"`.
- **Arbitrary strings later in a body**, even as standalone expression
  statements.
- **A `#` that is program data** — inside a string, f-string, raw string, or
  regex — is preserved byte-for-byte.
- **Shebang lines** like `#!/usr/bin/env python3` on line 1, unless
  `--remove-shebang` is set.

## What about files that do not parse?

By default the run stops on the first file that fails to parse as Python. With
`--continue-on-error`, pystrip reports the failure, keeps processing the other
files, and exits with code 2.

## Does pystrip reformat code?

No. It removes comments, docstrings, type annotations, and the blank lines left
behind by comment removal. It does not otherwise reflow or reformat code. Pair
it with a formatter such as `ruff format` or `black` if you want that.

## Will removing a comment ever change behaviour?

Almost never, with one upstream caveat: a PEP 263 encoding cookie
(`# -*- coding: latin-1 -*-`) is a comment that also changes how CPython decodes
the file. Removing it from a non-UTF-8 file can change behaviour. Keep such
files UTF-8, or exclude them.

## Is the Python API stable?

The names exported from the top-level `pystrip` package are public and stable.
Internal modules may change between releases. See the [Python API](api.md).

## How do I keep docstrings but drop comments (or vice versa)?

Use the `--keep-*` flags or the matching config keys. See
[Usage](usage.md#what-gets-removed) and [Configuration](configuration.md).
