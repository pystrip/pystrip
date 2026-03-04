"""Output formatters for pystrip violations."""

from __future__ import annotations

import json
from typing import Literal

from pystrip.stripper import Violation

FormatType = Literal["text", "json", "sarif", "gitlab", "github"]


def format_violations(
    violations: list[Violation],
    fmt: FormatType = "text",
) -> str:
    if fmt == "text":
        return _format_text(violations)
    if fmt == "json":
        return _format_json(violations)
    if fmt == "sarif":
        return _format_sarif(violations)
    if fmt == "gitlab":
        return _format_gitlab(violations)
    if fmt == "github":
        return _format_github(violations)
    raise ValueError(f"Unknown format: {fmt}")


def _format_text(violations: list[Violation]) -> str:
    lines: list[str] = []
    for v in violations:
        lines.append(f"{v.file}:{v.line}:{v.column}: {v.rule} {v.message}")
    return "\n".join(lines)


def _format_json(violations: list[Violation]) -> str:
    return json.dumps(
        [
            {
                "file": v.file,
                "line": v.line,
                "column": v.column,
                "rule": v.rule,
                "message": v.message,
            }
            for v in violations
        ],
        indent=2,
    )


def _format_sarif(violations: list[Violation]) -> str:
    rules: dict[str, dict[str, str]] = {}
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
                        "version": "0.1.0",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def _format_gitlab(violations: list[Violation]) -> str:
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
    return json.dumps(issues, indent=2)


def _format_github(violations: list[Violation]) -> str:
    lines: list[str] = []
    for v in violations:
        lines.append(
            f"::notice file={v.file},line={v.line},col={v.column},title={v.rule}::{v.message}"
        )
    return "\n".join(lines)
