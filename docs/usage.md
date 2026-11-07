# Usage

```bash
pystrip [paths ...] [options]
```

`paths` are files or directories (default: the current directory). Directories
are searched recursively unless `--no-recursive` is given.

## Common commands

```bash
# Check mode for CI: exit 1 if anything would change, write nothing
pystrip . --check

# Strip in place
pystrip ./src --in-place

# Preview changes as a unified diff
pystrip ./src --diff

# Write results to a separate directory, leaving inputs untouched
pystrip ./src --output-dir build/stripped

# Read from stdin, write stripped code to stdout
pystrip - < input.py > output.py
```

## What gets removed

By default pystrip removes comments, docstrings, type annotations, and the blank
lines left behind by comment removal. Narrow the scope with the `--keep-*`
flags:

| Flag | Effect |
|------|--------|
| `--keep-docstrings` | Keep docstrings; still strip comments and annotations. |
| `--keep-comments` | Keep comments; still strip docstrings and annotations. |
| `--keep-type-annotations` | Keep parameter, return, and variable annotations. |
| `--keep-blank` | Keep blank lines introduced by comment removal. |
| `--remove-shebang` | Also remove a `#!` shebang on line 1 (kept by default). |
| `--use-pass` | Use `pass` instead of `...` for emptied bodies. |

## Selecting files

| Flag | Effect |
|------|--------|
| `--exclude PATH` | Exclude a path fragment (repeatable). |
| `--exclude-glob PATTERN` | Exclude files whose name matches a glob (repeatable). |
| `--no-recursive` | Process only direct children of each directory. |
| `--jobs N` | Number of worker processes. |

## Output and diagnostics

| Flag | Effect |
|------|--------|
| `--format {text,json,sarif,gitlab,github}` | Violation output format. See [Output formats](output-formats.md). |
| `--quiet` | Suppress the progress spinner and summary. |
| `--verbose` | Print per-removal diagnostics to stderr. |
| `--continue-on-error` | Keep going when a file fails to parse; report it and exit 2. |
| `--config PATH` | Load configuration from a specific TOML file. |

## stdin mode

When `-` is the sole path, pystrip reads source from stdin. In normal mode it
writes the stripped code to stdout; in `--check` mode it emits violations
instead. `--in-place`, `--output-dir`, and `--diff` are not valid with stdin.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Clean — no changes needed. |
| 1 | Changes would be made (in `--check` mode). |
| 2 | Runtime, configuration, or CLI error. |

## Full option reference

Print the installed version with `pystrip --version`.

```text
usage: pystrip [-h] [--version] [--exclude PATH] [--exclude-glob PATTERN]
               [--keep-docstrings] [--keep-comments] [--keep-type-annotations]
               [--keep-blank] [--remove-shebang] [--use-pass] [--check]
               [--diff] [--in-place] [--output-dir DIR] [--no-recursive]
               [--jobs N] [--config PATH]
               [--format {text,json,sarif,gitlab,github}] [--quiet]
               [--verbose] [--continue-on-error]
               [paths ...]
```
