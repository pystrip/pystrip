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
| `--keep-header` | Keep the leading comment block of each file: shebang, encoding cookie, license banner. |
| `--remove-shebang` | Also remove a `#!` shebang on line 1 (kept by default). |
| `--use-pass` | Use `pass` instead of `...` for emptied bodies. |

### Rule selection

Every removal is reported under one of three rules: `COMMENT_REMOVED`,
`DOCSTRING_REMOVED`, `TYPE_ANNOTATION_REMOVED`. Instead of the `--keep-*` flags
you can pick rules directly, ruff-style. Names are case-insensitive, `ALL`
stands for every rule, and `--ignore` is applied after `--select`:

```bash
# Only strip docstrings
pystrip . --select DOCSTRING_REMOVED

# Everything except type annotations
pystrip . --ignore type_annotation_removed

# Repeatable or comma-separated
pystrip . --select COMMENT_REMOVED,DOCSTRING_REMOVED
```

The two mechanisms compose: rule selection is resolved first, then any
`--keep-*` flag still wins. The same keys exist in
[configuration](configuration.md) as `select` and `ignore`.

### Inline pragmas

A file can protect parts of itself without being excluded:

| Pragma | Effect |
|--------|--------|
| `# pystrip: keep` inside a comment | That comment is kept. |
| `# pystrip: keep` trailing a statement | Nothing on that line is removed: a docstring, an annotated assignment (`x: int = 1  # pystrip: keep`), or the comment itself. |
| `# pystrip: skip-file` on its own comment line | The whole file is left untouched and reported as clean. |

```python
# Copyright 2026 Example Corp  # pystrip: keep
"""Public module docstring, part of the API."""  # pystrip: keep

def f(x: int) -> int:
    # Explains a non-obvious invariant  # pystrip: keep
    return x  # removed
```

For a multi-line license banner, `--keep-header` is shorter than one pragma per
line: it protects the run of comment lines that starts on line 1 and ends at the
first blank or code line.

## Selecting files

Directories yield `.py`, `.pyi`, and `.ipynb` files. Type annotations are never
removed from `.pyi` stubs, since annotations are their whole content. In a
notebook, only the `source` of code cells is stripped; markdown cells, outputs,
and metadata are untouched, IPython line magics (`%time`, `!pip`) are preserved,
and a cell starting with a cell magic (`%%bash`) is left alone. Violations in a
notebook are reported as `notebook.ipynb#cell3:line:col`.

| Flag | Effect |
|------|--------|
| `--exclude PATH` | Exclude a path fragment (repeatable). |
| `--exclude-glob PATTERN` | Exclude files whose name matches a glob (repeatable). |
| `--respect-gitignore` | Skip files ignored by git (`git check-ignore`, so nested `.gitignore` files and global excludes apply). A path given explicitly is always processed. Outside a repository nothing is skipped. |
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

`--stdin-filename PATH` tells pystrip which file the stream belongs to. The path
appears in violations instead of `<stdin>`, and its suffix selects `.pyi` or
`.ipynb` handling. This is how editors wire pystrip in as a formatter:

```bash
pystrip - --stdin-filename src/app.py < src/app.py
```

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
