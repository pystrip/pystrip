"""Tests for output formatters."""

from __future__ import annotations

import json

from pystrip.reporting import format_violations
from pystrip.stripper import Violation


def make_violation(**kwargs: object) -> Violation:
    defaults: dict[str, object] = {
        "file": "test.py",
        "line": 1,
        "column": 0,
        "rule": "DOCSTRING_REMOVED",
        "message": "Module docstring removed",
    }
    defaults.update(kwargs)
    return Violation(**defaults)  # type: ignore[arg-type]


class TestJsonFormat:
    def test_valid_json(self) -> None:
        violations = [make_violation()]
        output = format_violations(
            violations,
            fmt="json",
            summary={
                "files_changed": 1,
                "total_violations": 1,
                "comments_removed": 0,
                "docstrings_removed": 1,
            },
        )
        data = json.loads(output)
        assert isinstance(data, dict)
        assert isinstance(data["violations"], list)
        assert data["violations"][0]["file"] == "test.py"
        assert data["violations"][0]["line"] == 1
        assert data["violations"][0]["rule"] == "DOCSTRING_REMOVED"
        assert data["summary"]["docstrings_removed"] == 1

    def test_empty_violations(self) -> None:
        output = format_violations([], fmt="json")
        assert json.loads(output) == {"violations": []}


class TestGitlabFormat:
    def test_valid_gitlab(self) -> None:
        violations = [make_violation()]
        output = format_violations(
            violations,
            fmt="gitlab",
            summary={
                "files_changed": 1,
                "total_violations": 1,
                "comments_removed": 0,
                "docstrings_removed": 1,
            },
        )
        data = json.loads(output)
        assert isinstance(data, list)
        assert "fingerprint" in data[0]
        assert data[0]["location"]["path"] == "test.py"
        assert "Changed 1 file(s)" in data[1]["description"]

    def test_empty(self) -> None:
        output = format_violations([], fmt="gitlab")
        assert json.loads(output) == []


class TestSarifFormat:
    def test_valid_sarif(self) -> None:
        violations = [make_violation()]
        output = format_violations(
            violations,
            fmt="sarif",
            summary={
                "files_changed": 1,
                "total_violations": 1,
                "comments_removed": 0,
                "docstrings_removed": 1,
            },
        )
        data = json.loads(output)
        assert data["version"] == "2.1.0"
        assert "runs" in data
        assert data["runs"][0]["results"][0]["ruleId"] == "DOCSTRING_REMOVED"
        assert data["runs"][0]["properties"]["pystripSummary"]["docstrings_removed"] == 1


class TestGithubFormat:
    def test_github_annotation(self) -> None:
        violations = [make_violation()]
        output = format_violations(
            violations,
            fmt="github",
            summary={
                "files_changed": 1,
                "total_violations": 1,
                "comments_removed": 0,
                "docstrings_removed": 1,
            },
        )
        assert "::notice" in output
        assert "file=test.py" in output
        assert "line=1" in output
        assert "title=pystrip summary" in output


class TestTextFormat:
    def test_text_format(self) -> None:
        violations = [make_violation()]
        output = format_violations(violations, fmt="text")
        assert "test.py:1:0" in output
        assert "DOCSTRING_REMOVED" in output
