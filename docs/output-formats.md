# Output formats

Select a format with `--format`. Every removal is reported as a violation with a
file, line, column, and rule (`COMMENT_REMOVED`, `DOCSTRING_REMOVED`, or
`TYPE_ANNOTATION_REMOVED`).

## text (default)

Human-readable, one violation per line, plus a summary on stderr.

```text
src/app.py:1:0: DOCSTRING_REMOVED Module docstring removed
src/app.py:12:4: COMMENT_REMOVED Trailing comment removed
```

## json

A machine-readable object with a `violations` array and a `summary`.

```bash
pystrip . --check --format json
```

```json
{
  "violations": [
    { "file": "src/app.py", "line": 1, "column": 0, "rule": "DOCSTRING_REMOVED", "message": "Module docstring removed" }
  ],
  "summary": {
    "files_changed": 1,
    "total_violations": 1,
    "comments_removed": 0,
    "docstrings_removed": 1,
    "annotations_removed": 0
  }
}
```

## sarif

[SARIF 2.1.0](https://sarifweb.azurewebsites.net/), suitable for GitHub code
scanning and other analysis dashboards.

```bash
pystrip . --check --format sarif > pystrip.sarif
```

## gitlab

A GitLab [Code Quality](https://docs.gitlab.com/ee/ci/testing/code_quality.html)
report. Each violation carries a stable fingerprint.

```bash
pystrip . --check --format gitlab > gl-code-quality-report.json
```

## github

GitHub Actions [workflow commands](https://docs.github.com/actions/using-workflows/workflow-commands-for-github-actions)
(`::notice`), which surface as annotations on the run and in the diff.

```bash
pystrip . --check --format github
```
