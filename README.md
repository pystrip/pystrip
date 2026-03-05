# Pystrip

[![CI](https://github.com/pystrip/pystrip/actions/workflows/ci.yml/badge.svg)](https://github.com/pystrip/pystrip/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pystrip.svg?cacheSeconds=300)](https://pypi.org/project/pystrip/)
[![Python](https://img.shields.io/pypi/pyversions/pystrip.svg?cacheSeconds=300)](https://pypi.org/project/pystrip/)
[![Issues](https://img.shields.io/github/issues/pystrip/pystrip)](https://github.com/pystrip/pystrip/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/pystrip/pystrip)](https://github.com/pystrip/pystrip/pulls)
[![Ruff](https://img.shields.io/badge/lint-ruff-46a2f1)](https://github.com/astral-sh/ruff)
[![Ty](https://img.shields.io/badge/type%20check-ty-7c3aed)](https://github.com/astral-sh/ty)

Python tool to safely remove comments and docstrings from source files using [libcst](https://libcst.readthedocs.io/).

## Features

- Removes comments (inline and standalone)
- Removes docstrings (module, class, function)
- Removes type annotations (parameter hints, return types, variable annotations)
- Keeps regular string literals untouched
- Supports output formats: `text`, `json`, `sarif`, `gitlab`, `github`
- Works in CI with `--check`
- Supports config discovery and parallel processing

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
```

```bash
usage: pystrip [-h] [--exclude PATH] [--exclude-glob PATTERN] [--keep-docstrings] [--keep-type-annotations] [--check] [--diff] [--in-place] [--output-dir DIR] [--no-recursive] [--jobs N] [--keep-blank]
               [--config PATH] [--format {text,json,sarif,gitlab,github}] [--quiet] [--verbose]
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
  --keep-type-annotations
                        Keep type annotations and only strip comments/docstrings (default: None)
  --check               Do not write files; exit with code 1 if any file would change (default: False)
  --diff                Print unified diffs for changed files (default: False)
  --in-place            Write stripped output back to each input file (default: False)
  --output-dir DIR      Write changed files into DIR instead of modifying inputs (default: None)
  --no-recursive        Process only direct child files of each directory path (default: True)
  --jobs N              Number of worker processes to use (default: None)
  --keep-blank          Keep blank lines introduced by comment removal (default: None)
  --config PATH         Load configuration from a specific TOML file (default: None)
  --format {text,json,sarif,gitlab,github}
                        Output format for violations (default: None)
  --quiet               Suppress progress and summary output (default: False)
  --verbose             Print detailed removal diagnostics (default: False)
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

## Configuration

Use either `pyproject.toml` (`[tool.pystrip]`) or `.pystrip.toml` (`[pystrip]`).
`pyproject.toml` is recommended when pystrip is part of a project; `.pystrip.toml` is useful for standalone usage.

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
