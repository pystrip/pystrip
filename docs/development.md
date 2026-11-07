# Development

## Local setup

```bash
uv sync --group dev
```

## Run the CLI locally

```bash
uv run pystrip . --check
```

## Quality checks

Run all checks before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check src/pystrip
uv run python -m pytest --cov=pystrip --cov-report=term-missing
```

CI runs the same checks on Python 3.11, 3.12, and 3.13, and enforces a test
coverage floor of 80%.

## pre-commit hooks

Install the contributor hooks (ruff and basic hygiene) once:

```bash
uv run pre-commit install
```

Run them against the whole tree on demand:

```bash
uv run pre-commit run --all-files
```

## Documentation

The docs site is built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
uv sync --group docs
uv run mkdocs serve          # live preview at http://127.0.0.1:8000
uv run mkdocs build --strict # production build; fails on warnings
```

Pushing to `main` deploys the site to GitHub Pages via the `docs` workflow.

## Releasing

The version is derived from the git tag by `hatch-vcs`; there is no version to
bump in `pyproject.toml`.

1. Update `CHANGELOG.md`.
2. Tag the release: `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. Create a GitHub Release for that tag. Publishing the release triggers the
   `publish` workflow, which builds and uploads to PyPI via trusted publishing.

## Contributing

- Create a feature branch from `main`.
- Add or update tests for behavior changes.
- Keep the README and docs in sync with CLI flags and output.
- Open a pull request with a clear summary and test evidence.
