# pystrip

A production-grade Python tool to safely remove comments and docstrings from Python source files using [libcst](https://libcst.readthedocs.io/).

## Features

- Removes **comments** (inline and standalone)
- Removes **docstrings** (module, class, function level)
- **Never** modifies regular string literals
- Preserves formatting perfectly (indentation, blank lines, newlines)
- Multiple output formats: `text`, `json`, `sarif`, `gitlab`, `github`
- CI-ready with `--check` mode
- Automatic config discovery (`.pystrip.toml`, `pyproject.toml [tool.pystrip]`)
- File caching (sha256-based) to skip unchanged files
- Parallel processing via `ProcessPoolExecutor`

## Installation

```bash
uv venv
uv pip install -e .
```

## Usage

```bash
# Check mode (CI-friendly)
pystrip . --check

# Strip in-place
pystrip . --in-place

# Strip to output directory
pystrip . --output-dir stripped/

# Keep docstrings, only remove comments
pystrip . --keep-docstrings

# JSON output
pystrip . --check --format json

# Show diff
pystrip . --diff
```

## Configuration

### pyproject.toml

```toml
[tool.pystrip]
remove_comments = true
remove_docstrings = true
exclude = ["tests/"]
exclude_glob = ["*.generated.py"]
line_length = 100
jobs = 4
cache = true
```

### .pystrip.toml

```toml
[pystrip]
remove_comments = true
remove_docstrings = true
exclude = ["tests/"]
```

## CI Examples

### GitHub Actions

```yaml
- run: pystrip . --check --format github
```

### GitLab CI

```yaml
script:
  - pystrip . --check --format gitlab > gl-code-quality-report.json
```

### Pre-commit

```yaml
repos:
  - repo: local
    hooks:
      - id: pystrip
        name: pystrip
        entry: pystrip
        args: [--check]
        language: system
        types: [python]
```

## Before / After

**Before:**
```python
"""Module docstring."""

# This is a comment
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"  # inline comment
```

**After:**
```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Clean (no violations) |
| 1    | Violations found (in `--check` mode) |
| 2    | Runtime error |
