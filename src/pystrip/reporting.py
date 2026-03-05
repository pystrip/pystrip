"""Output formatters for pystrip violations."""

from __future__ import annotations

import json
from typing import Any, Literal

from pystrip import __version__
from pystrip.stripper import Violation

FormatType = Literal["text", "json", "sarif", "gitlab", "github"]


def format_violations(
    violations: list[Violation],
    fmt: FormatType = "text",
    summary: dict[str, Any] | None = None,
) -> str:
    if fmt == "text":
        return _format_text(violations)
    if fmt == "json":
        return _format_json(violations, summary=summary)
    if fmt == "sarif":
        return _format_sarif(violations, summary=summary)
    if fmt == "gitlab":
        return _format_gitlab(violations, summary=summary)
    if fmt == "github":
        return _format_github(violations, summary=summary)
    raise ValueError(f"Unknown format: {fmt}")


def _format_text(violations: list[Violation]) -> str:
    lines: list[str] = []
    for v in violations:
        lines.append(f"{v.file}:{v.line}:{v.column}: {v.rule} {v.message}")
    return "\n".join(lines)


def _format_json(
    violations: list[Violation],
    summary: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "violations": [
            {
                "file": v.file,
                "line": v.line,
                "column": v.column,
                "rule": v.rule,
                "message": v.message,
            }
            for v in violations
        ]
    }
    if summary is not None:
        payload["summary"] = summary
    return json.dumps(payload, indent=2)


def _format_sarif(
    violations: list[Violation],
    summary: dict[str, Any] | None = None,
) -> str:
    rules: dict[str, dict[str, object]] = {}
    results: list[dict[str, object]] = []

    for v in violations:
        if v.rule not in rules:
            rules[v.rule] = {
                "id": v.rule,
                "name": v.rule.replace("_", " ").title(),
                "shortDescription": {"text": v.message},
            }
        results.append(
            {
                "ruleId": v.rule,
                "message": {"text": v.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": v.file},
                            "region": {
                                "startLine": v.line,
                                "startColumn": v.column + 1,
                            },
                        }
                    }
                ],
            }
        )

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pystrip",
                        "version": __version__,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "properties": {"pystripSummary": summary or {}},
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def _format_gitlab(
    violations: list[Violation],
    summary: dict[str, Any] | None = None,
) -> str:
    import hashlib

    issues: list[dict[str, object]] = []
    for v in violations:
        fingerprint = hashlib.md5(  # noqa: S324
            f"{v.file}:{v.line}:{v.column}:{v.rule}".encode()
        ).hexdigest()
        issues.append(
            {
                "description": v.message,
                "fingerprint": fingerprint,
                "severity": "info",
                "location": {
                    "path": v.file,
                    "lines": {"begin": v.line},
                },
            }
        )

    if summary is not None:
        summary_text = (
            f"Changed {summary.get('files_changed', 0)} file(s), "
            f"{summary.get('total_violations', 0)} violation(s), "
            f"{summary.get('docstrings_removed', 0)} docstring(s), "
            f"{summary.get('comments_removed', 0)} comment(s), "
            f"{summary.get('annotations_removed', 0)} annotation(s)."
        )
        issues.append(
            {
                "description": summary_text,
                "fingerprint": hashlib.md5(summary_text.encode()).hexdigest(),  # noqa: S324
                "severity": "info",
                "location": {"path": ".", "lines": {"begin": 1}},
            }
        )

    return json.dumps(issues, indent=2)


def _format_github(
    violations: list[Violation],
    summary: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    for v in violations:
        lines.append(
            f"::notice file={v.file},line={v.line},col={v.column},title={v.rule}::{v.message}"
        )

    if summary is not None:
        lines.append(
            "::notice title=pystrip summary::"
            f"Changed {summary.get('files_changed', 0)} file(s), "
            f"{summary.get('total_violations', 0)} violation(s), "
            f"{summary.get('docstrings_removed', 0)} docstring(s), "
            f"{summary.get('comments_removed', 0)} comment(s), "
            f"{summary.get('annotations_removed', 0)} annotation(s)."
        )

    return "\n".join(lines)
