# Integrations

## pre-commit

pystrip ships [pre-commit](https://pre-commit.com/) hook definitions. Add it to a
project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pystrip/pystrip
    rev: v1.4.0
    hooks:
      - id: pystrip
```

Two hooks are available:

| Hook id | Behaviour |
|---------|-----------|
| `pystrip` | Strips files in place (`--in-place`). pre-commit fails the commit when a file was rewritten, so you review and re-stage. |
| `pystrip-check` | Verifies only (`--check`); fails if anything would change but writes nothing. |

Pass extra arguments with `args`:

```yaml
      - id: pystrip
        args: [--in-place, --keep-docstrings]
```

## GitHub Actions

### Reusable action

Use the composite action published from this repository:

```yaml
jobs:
  pystrip:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pystrip/pystrip@v1
        with:
          paths: "src"
          args: "--check --format github"
```

Inputs:

| Input | Default | Description |
|-------|---------|-------------|
| `paths` | `.` | Files or directories to process. |
| `args` | `--check --format github` | Arguments passed to pystrip. |
| `version` | latest | pystrip version to install. |
| `python-version` | `3.11` | Python used to run pystrip. |

### Plain workflow step

If you prefer not to use the action:

```yaml
      - run: pipx run pystrip . --check --format github
```

The `--format github` output turns each surviving comment or docstring into an
inline annotation on the pull request.

## GitLab CI

Emit a Code Quality report that GitLab renders in merge requests:

```yaml
pystrip:
  image: python:3.11
  script:
    - pip install pystrip
    - pystrip . --check --format gitlab > gl-code-quality-report.json
  artifacts:
    reports:
      codequality: gl-code-quality-report.json
```
