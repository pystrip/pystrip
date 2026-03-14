# Pystrip

[![CI](https://github.com/pystrip/pystrip/actions/workflows/ci.yml/badge.svg)](https://github.com/pystrip/pystrip/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pystrip.svg?cacheSeconds=300)](https://pypi.org/project/pystrip/)
[![Python](https://img.shields.io/pypi/pyversions/pystrip.svg?cacheSeconds=300)](https://pypi.org/project/pystrip/)
[![Issues](https://img.shields.io/github/issues/pystrip/pystrip)](https://github.com/pystrip/pystrip/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/pystrip/pystrip)](https://github.com/pystrip/pystrip/pulls)
[![Ruff](https://img.shields.io/badge/lint-ruff-46a2f1)](https://github.com/astral-sh/ruff)
[![Ty](https://img.shields.io/badge/type%20check-ty-7c3aed)](https://github.com/astral-sh/ty)

![Banner](docs/banner.png)

Python tool to safely remove comments, docstrings, and type annotations from source files using [libcst](https://libcst.readthedocs.io/).

## Features

- Removes comments (inline and standalone)
- Removes docstrings (module, class, function)
- Removes type annotations (parameter hints, return types, variable annotations)
- Keeps regular string literals untouched
- Supports output formats: `text`, `json`, `sarif`, `gitlab`, `github`
- Works in CI with `--check`
- Supports config discovery and parallel processing

## What pystrip will not remove

- String literals that are not docstrings. A string only counts as a docstring when it is the first statement in a module, class, or function body.
- String literals that merely look like comments, such as `"value # not a comment"`.
- Arbitrary strings later in a body, even if they are standalone expression statements.
- Shebang lines like `#!/usr/bin/env python3` unless `--remove-shebang` is set.
- Files that fail to parse as Python. By default the run stops on the first such error; with `--continue-on-error`, pystrip reports the failure and keeps processing other files.

Docstring detection is syntax-based, not text-based. That means pystrip does not try to guess intent from quote style or wording; it only removes a literal string expression in the docstring position.

## Installation

```bash
pip install pystrip
```

## Usage

```bash
# Check mode (CI)
pystrip . --check

# Apply changes in place
pystrip ./src/ --in-place

# Read from stdin and write stripped code to stdout
pystrip - < input.py > output.py
```

```bash
usage: pystrip [-h] [--exclude PATH] [--exclude-glob PATTERN] [--keep-docstrings] [--keep-comments] [--keep-type-annotations] [--keep-blank] [--remove-shebang] [--use-pass] [--check]
               [--diff] [--in-place] [--output-dir DIR] [--no-recursive] [--jobs N] [--config PATH] [--format {text,json,sarif,gitlab,github}] [--quiet] [--verbose]
               [--continue-on-error]
               [paths ...]

Remove comments and docstrings from Python source files.

positional arguments:
  paths                 Files or directories to process (default: ['.'])

options:
  -h, --help            show this help message and exit
  --exclude PATH        Exclude a file or directory path (repeatable) (default: None)
  --exclude-glob PATTERN
                        Exclude paths by glob pattern (repeatable) (default: None)
  --keep-docstrings     Keep docstrings and only strip comments (default: None)
  --keep-comments       Keep comments and only strip docstrings (default: None)
  --keep-type-annotations
                        Keep type annotations and only strip comments/docstrings (default: None)
  --keep-blank          Keep blank lines introduced by comment removal (default: None)
  --remove-shebang      Remove shebang lines (#!/...) from files (kept by default) (default: None)
  --use-pass            Use 'pass' instead of '...' for empty body placeholders (default: None)
  --check               Do not write files; exit with code 1 if any file would change (default: False)
  --diff                Print unified diffs for changed files (default: False)
  --in-place            Write stripped output back to each input file (default: False)
  --output-dir DIR      Write changed files into DIR instead of modifying inputs (default: None)
  --no-recursive        Process only direct child files of each directory path (default: True)
  --jobs N              Number of worker processes to use (default: None)
  --config PATH         Load configuration from a specific TOML file (default: None)
  --format {text,json,sarif,gitlab,github}
                        Output format for violations (default: None)
  --quiet               Suppress progress and summary output (default: False)
  --verbose             Print detailed removal diagnostics (default: False)
  --continue-on-error   Continue processing remaining files when a file fails to parse/process (default: False)
```

Output example:

```bash
⠇ Processing 10 file(s)...
src/pystrip/__init__.py:1:0: DOCSTRING_REMOVED Module docstring removed
src/pystrip/__main__.py:1:0: DOCSTRING_REMOVED Module docstring removed
...
src/pystrip/visitor.py:1:0: DOCSTRING_REMOVED Module docstring removed
Changed 10 file(s), 63 violation(s), 26 docstring(s), 37 comment(s), 0 annotation(s).
```

When using `-` as the sole input path, pystrip reads source from stdin. In normal mode it writes stripped code to stdout; in `--check` mode it emits violations instead. `--in-place`, `--output-dir`, and `--diff` are not available with stdin input.

## Configuration

Use either `pyproject.toml` (`[tool.pystrip]`) or `.pystrip.toml` (`[pystrip]`).
`pyproject.toml` is recommended when pystrip is part of a project; `.pystrip.toml` is useful for standalone usage.
Invalid config values (for example `jobs = "4"`) fail fast with exit code `2` and a clear error message.

```toml
[tool.pystrip]
remove_comments = true
remove_docstrings = true
remove_blank_lines = true
remove_type_annotations = true
exclude = ["tests/"]
exclude_glob = ["*.generated.py"]
jobs = 4
```

## Output and CI

```bash
# GitHub annotations
pystrip . --check --format github

# GitLab code-quality report
pystrip . --check --format gitlab > gl-code-quality-report.json
```

## Development

Developer setup, quality checks, and contribution workflow are documented in [docs/development.md](docs/development.md).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Clean (no changes needed) |
| 1    | Changes would be made in `--check` mode |
| 2    | Runtime or CLI error |
