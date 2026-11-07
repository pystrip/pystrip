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
| `keep_header` | bool | `false` | Keep the leading comment block (shebang, encoding cookie, license banner). |
| `select` | list[str] | all rules | Rules to enable: `COMMENT_REMOVED`, `DOCSTRING_REMOVED`, `TYPE_ANNOTATION_REMOVED`, or `ALL`. |
| `ignore` | list[str] | `[]` | Rules to disable, applied after `select`. |
| `respect_gitignore` | bool | `false` | Skip git-ignored files when searching directories. |
| `exclude` | list[str] | `[]` | Path fragments to skip. |
| `exclude_glob` | list[str] | `[]` | File-name globs to skip. |
| `line_length` | int | `100` | Reserved for formatting. |
| `jobs` | int | `1` | Worker processes. |

`select` / `ignore` and the `remove_*` switches describe the same thing. When
either `select` or `ignore` is set, it decides the three rule switches and the
`remove_comments` / `remove_docstrings` / `remove_type_annotations` keys are
ignored; a configuration that sets neither behaves exactly as before.

## Example

```toml
[tool.pystrip]
select = ["ALL"]
ignore = ["TYPE_ANNOTATION_REMOVED"]
keep_header = true
respect_gitignore = true
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
