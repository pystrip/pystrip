# Development

## Local setup

```bash
uv sync
```

## Run the CLI locally

```bash
uv run pystrip . --check --no-cache
```

## Quality checks

Run all checks before opening a pull request:

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check src/pystrip
uv run pytest -v
```

## Contributing

- Create a feature branch from `main`.
- Add or update tests for behavior changes.
- Keep README/docs in sync with CLI flags and output.
- Open a pull request with a clear summary and test evidence.
