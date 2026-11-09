# Python API

pystrip exposes a small, stable public API for stripping a single source string.
It is useful for editor plugins, build steps, or tests.

```python
from pystrip import strip_code, StripConfig, StripResult, Violation
```

## `strip_code`

```python
def strip_code(source: str, config: StripConfig) -> StripResult: ...
```

Strip comments, docstrings, and/or type annotations from a source string. Raises
`ValueError` if the source cannot be parsed as Python.

```python
from pystrip import strip_code, StripConfig

source = '''
def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"  # friendly
'''

result = strip_code(source, StripConfig(filename="greet.py"))
print(result.changed)  # True
print(result.modified_code)  # def greet(name): ...
for v in result.violations:
    print(v.rule, v.line, v.message)
```

## `StripConfig`

Configuration for a single strip operation.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `remove_comments` | bool | `True` | Remove comments. |
| `remove_docstrings` | bool | `True` | Remove docstrings. |
| `remove_blank_lines` | bool | `True` | Remove blank lines left by comment removal. |
| `remove_type_annotations` | bool | `True` | Remove type annotations. |
| `remove_shebang` | bool | `False` | Remove a line-1 shebang. |
| `use_pass` | bool | `False` | Use `pass` instead of `...` for emptied bodies. |
| `keep_header` | bool | `False` | Keep the leading comment block (see `--keep-header`). |
| `filename` | str | `"<unknown>"` | Name used in violations and parse errors. A `.pyi` suffix disables annotation removal. |

## `StripResult`

| Field | Type | Meaning |
|-------|------|---------|
| `modified_code` | str | The stripped source. |
| `changed` | bool | Whether `modified_code` differs from the input. |
| `violations` | list[Violation] | One entry per removal. |
| `skipped` | bool | `True` when the source carried `# pystrip: skip-file` and was returned as-is. |

## `strip_notebook`

```python
from pystrip.notebook import strip_notebook


def strip_notebook(text: str, config: StripConfig) -> StripResult: ...
```

Strip every code cell of a Jupyter notebook given as its JSON text. Returns the
re-serialised notebook in `modified_code` (Jupyter's own one-space indentation,
so an unchanged notebook round-trips byte-for-byte). Violations use
`<filename>#cell<N>` as their file. Raises `ValueError` if the text is not a
notebook or a cell does not parse.

## `Violation`

| Field | Type | Meaning |
|-------|------|---------|
| `file` | str | Source filename. |
| `line` | int | 1-based line. |
| `column` | int | 0-based column. |
| `rule` | str | `COMMENT_REMOVED`, `DOCSTRING_REMOVED`, or `TYPE_ANNOTATION_REMOVED`. |
| `message` | str | Human-readable description. |

## Stability

Only the names exported from the top-level `pystrip` package are public. Modules
such as `pystrip.visitor` and `pystrip.cli` are internal and may change between
releases.
