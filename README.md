# Pystrip

[![CI](https://github.com/pystrip/pystrip/actions/workflows/ci.yml/badge.svg)](https://github.com/pystrip/pystrip/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pystrip.svg)](https://pypi.org/project/pystrip/)
[![Python](https://img.shields.io/pypi/pyversions/pystrip.svg)](https://pypi.org/project/pystrip/)
[![Issues](https://img.shields.io/github/issues/pystrip/pystrip)](https://github.com/pystrip/pystrip/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/pystrip/pystrip)](https://github.com/pystrip/pystrip/pulls)
[![Ruff](https://img.shields.io/badge/lint-ruff-46a2f1)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/type%20check-mypy-2a6db2)](https://mypy-lang.org/)

Python tool to safely remove comments and docstrings from source files using [libcst](https://libcst.readthedocs.io/).

## Features

- Removes comments (inline and standalone)
- Removes docstrings (module, class, function)
- Keeps regular string literals untouched
- Supports output formats: `text`, `json`, `sarif`, `gitlab`, `github`
- Works in CI with `--check`
- Supports config discovery, caching, and parallel processing

## Installation

```bash
pip install pystrip
```

## Usage

```bash
# Check mode (CI)
pystrip . --check

# Apply changes in place
pystrip . --in-place

# Keep docstrings; only remove comments
pystrip . --keep-docstrings

# Keep blank lines after comment removal
pystrip . --keep-blank

# Disable recursive directory walk
pystrip . --no-recursive

# Print each removed comment location
pystrip . --check --verbose
```

## Configuration

Use either `pyproject.toml` (`[tool.pystrip]`) or `.pystrip.toml` (`[pystrip]`).
`pyproject.toml` is recommended when pystrip is part of a project; `.pystrip.toml` is useful for standalone usage.

```toml
[tool.pystrip]
remove_comments = true
remove_docstrings = true
remove_blank_lines = true
exclude = ["tests/"]
exclude_glob = ["*.generated.py"]
jobs = 4
cache = true
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
