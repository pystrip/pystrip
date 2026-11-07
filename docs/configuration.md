# Configuration

pystrip reads configuration from a TOML file. Use either `pyproject.toml`
(`[tool.pystrip]`) or a standalone `.pystrip.toml` (`[pystrip]`).
`pyproject.toml` is the natural choice inside a project; `.pystrip.toml` suits
standalone use.

## Keys

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `remove_comments` | bool | `true` | Remove comments. |
| `remove_docstrings` | bool | `true` | Remove docstrings. |
| `remove_type_annotations` | bool | `true` | Remove type annotations. |
| `remove_blank_lines` | bool | `true` | Remove blank lines left by comment removal. |
| `remove_shebang` | bool | `false` | Remove a line-1 `#!` shebang. |
| `use_pass` | bool | `false` | Use `pass` instead of `...` for emptied bodies. |
| `exclude` | list[str] | `[]` | Path fragments to skip. |
| `exclude_glob` | list[str] | `[]` | File-name globs to skip. |
| `line_length` | int | `100` | Reserved for formatting. |
| `jobs` | int | `1` | Worker processes. |

## Example

```toml
[tool.pystrip]
remove_comments = true
remove_docstrings = true
remove_type_annotations = true
remove_blank_lines = true
exclude = ["tests/"]
exclude_glob = ["*.generated.py"]
jobs = 4
```

## Precedence

Later sources override earlier ones:

1. Built-in defaults.
2. `[tool.pystrip]` in `pyproject.toml` (in the project root).
3. `[pystrip]` in `.pystrip.toml` (in the project root).
4. An explicit `--config PATH`.
5. Command-line flags.

The project root is discovered by walking upward from the current directory to
the first folder containing `pyproject.toml` or `.git`.

## Strict validation

Invalid values fail fast with exit code `2` and a clear message instead of being
silently ignored. For example, `jobs = "4"` (a string, not an integer) or
`jobs = -1` (not positive) is rejected.
