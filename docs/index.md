# pystrip

![Banner](banner.png)

**pystrip** safely removes comments, docstrings, and type annotations from Python
source files. It parses each file into a concrete syntax tree with
[libcst](https://libcst.readthedocs.io/), so it only ever touches real syntax:
string literals that are not docstrings are preserved byte-for-byte, and a `#`
that lives inside a string or f-string is never mistaken for a comment.

[Get started](installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/pystrip/pystrip){ .md-button }

## Why pystrip

- **Syntax-based, not text-based.** A string is only removed when it sits in the
  docstring position (first statement of a module, class, or function). Quote
  style and wording are irrelevant.
- **It reports what it removed.** Every removal is a structured violation with a
  file, line, column, and rule, emitted in `text`, `json`, `sarif`, `gitlab`, or
  `github` format.
- **It fits CI.** Run `pystrip . --check` to fail a build when a file still
  carries comments or docstrings, without modifying anything.
- **It is fast on large trees.** Files are processed in parallel worker
  processes, controlled by `--jobs`.

## A first run

```bash
pip install pystrip

# Report what would change, without writing anything
pystrip . --check

# Strip in place
pystrip ./src --in-place
```

```python
# before
def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"  # friendly
```

```python
# after
def greet(name):
    return f"hello {name}"
```

## Where to go next

- [Installation](installation.md) — pip, pipx, uv.
- [Usage](usage.md) — every flag, stdin mode, and exit codes.
- [Configuration](configuration.md) — `pyproject.toml` and `.pystrip.toml`.
- [Output formats](output-formats.md) — text, JSON, SARIF, GitLab, GitHub.
- [Integrations](integrations.md) — pre-commit, GitHub Actions, GitLab CI.
- [Python API](api.md) — call `strip_code` from your own code.
