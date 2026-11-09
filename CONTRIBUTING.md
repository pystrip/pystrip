# Contributing to pystrip

Thanks for your interest in improving pystrip. This project values small,
well-tested changes with clear reasoning.

## Development setup

pystrip uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/pystrip/pystrip
cd pystrip
uv sync --group dev
```

## Before you open a pull request

Run the full check suite. CI runs the same on Python 3.11, 3.12, and 3.13.

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check src/pystrip
uv run python -m pytest --cov=pystrip --cov-report=term-missing
```

Optionally install the contributor pre-commit hooks:

```bash
uv run pre-commit install
```

## Expectations

- **Add a test for every behaviour change.** pystrip edits source code, so a
  regression is costly. Tests assert on the program, not just that it compiles.
- **Keep changes focused.** One concern per pull request.
- **Keep docs in sync.** If you add or change a CLI flag, config key, or output
  format, update the README and `docs/`.
- **Update `CHANGELOG.md`** under an `Unreleased` or new version heading.

## Reporting bugs

Open an issue with a minimal Python input that reproduces the problem, the exact
command, and the pystrip and Python versions. See the bug report template.

## How releases work

The version comes from the git tag via `hatch-vcs`; there is nothing to bump in
`pyproject.toml`. See [Development → Releasing](docs/development.md#releasing).
