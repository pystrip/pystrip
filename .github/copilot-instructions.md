# Copilot Instructions for pystrip

## Project purpose and boundaries
- `pystrip` is a CLI + library that removes Python comments/docstrings using CST transforms (not regex/text ops).
- Keep behavior deterministic and machine-readable for CI outputs (`text`, `json`, `sarif`, `gitlab`, `github`).
- Public library surface is intentionally small: `strip_code`, `StripConfig`, `StripResult`, `Violation` (`src/pystrip/__init__.py`).

## Architecture and data flow
- CLI entrypoint: `src/pystrip/cli.py` (`main()` → `_run(args)`).
- `_run` flow is: discover root (`discovery.py`) → load config (`config.py`) → apply CLI overrides → collect files (`utils.py`) → process via `strip_code` (`stripper.py`) → format outputs (`reporting.py`) → set exit code.
- Transformation logic lives in `src/pystrip/visitor.py` (`PyStripTransformer`) and must stay libcst-based.
- `stripper.py` parses with `libcst.parse_module`, wraps with `MetadataWrapper`, and records `Violation` entries from visitor metadata positions.

## Behavior contracts to preserve
- Docstring detection is only first statement expression string in module/class/function (`_is_docstring_node`), not arbitrary strings.
- If removing a docstring would empty a module/function/class body, insert `pass` (see `visitor.py`, tested in `tests/test_stripper.py`).
- Inline and leading comments generate `COMMENT_REMOVED`; docstrings generate `DOCSTRING_REMOVED`.
- `--check` returns exit code `1` when files would change, `0` otherwise; unexpected/runtime errors return `2`.
- `--verbose` writes per-comment diagnostics and per-file removed-comment counts to stderr.
- Output summary counts (files/violations/docstrings/comments) are part of formatter expectations (`tests/test_reporting.py`, `tests/test_cli.py`).

## Config and precedence
- Config model: `PyStripConfig` in `src/pystrip/config.py`.
- Priority is: defaults < `pyproject.toml` `[tool.pystrip]` < `.pystrip.toml` < explicit `--config` < CLI overrides.
- CLI booleans invert behavior via “keep” flags (`--keep-docstrings` sets `remove_docstrings=False`, `--keep-blank` sets `remove_blank_lines=False`).

## File discovery and path handling
- File selection is centralized in `collect_python_files` (`src/pystrip/utils.py`).
- `exclude` is substring match on full path string; `exclude_glob` matches filename (`fnmatch` on `py_file.name`).
- Current `--output-dir` behavior writes changed files as `<output-dir>/<basename>` (no directory mirroring); preserve unless explicitly changing UX/spec.

## Developer workflow (use uv)
- Setup: `uv sync`
- Run CLI locally: `uv run pystrip . --check`
- Required quality checks (see `docs/development.md`):
  - `uv sync --group dev`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run ty check src/pystrip`
  - `uv run pytest -v`

## Implementation style in this repo
- Prefer small typed dataclasses + pure helpers over stateful abstractions.
- Keep CLI flags and help text synchronized with README/docs/tests when adding/removing options.
- Add/adjust tests in `tests/` for every behavior change; this repo validates many user-facing semantics via subprocess CLI tests.
