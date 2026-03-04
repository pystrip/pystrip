# Development

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest ruff mypy
```

## Run the CLI locally

```bash
python -m pystrip . --check --no-cache
```

## Quality checks

Run all checks before opening a pull request:

```bash
ruff check .
ruff format --check .
mypy src/pystrip
pytest -v
```

## Contributing

- Create a feature branch from `main`.
- Add or update tests for behavior changes.
- Keep README/docs in sync with CLI flags and output.
- Open a pull request with a clear summary and test evidence.
