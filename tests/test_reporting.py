"""Tests for output formatters."""

from __future__ import annotations

import json

import pytest

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
        output = format_violations(violations, fmt="json")
        data = json.loads(output)
        assert isinstance(data, list)
        assert data[0]["file"] == "test.py"
        assert data[0]["line"] == 1
        assert data[0]["rule"] == "DOCSTRING_REMOVED"

    def test_empty_violations(self) -> None:
        output = format_violations([], fmt="json")
        assert json.loads(output) == []


class TestGitlabFormat:
    def test_valid_gitlab(self) -> None:
        violations = [make_violation()]
        output = format_violations(violations, fmt="gitlab")
        data = json.loads(output)
        assert isinstance(data, list)
        assert "fingerprint" in data[0]
        assert data[0]["location"]["path"] == "test.py"

    def test_empty(self) -> None:
        output = format_violations([], fmt="gitlab")
        assert json.loads(output) == []


class TestSarifFormat:
    def test_valid_sarif(self) -> None:
        violations = [make_violation()]
        output = format_violations(violations, fmt="sarif")
        data = json.loads(output)
        assert data["version"] == "2.1.0"
        assert "runs" in data
        assert data["runs"][0]["results"][0]["ruleId"] == "DOCSTRING_REMOVED"


class TestGithubFormat:
    def test_github_annotation(self) -> None:
        violations = [make_violation()]
        output = format_violations(violations, fmt="github")
        assert "::notice" in output
        assert "file=test.py" in output
        assert "line=1" in output


class TestTextFormat:
    def test_text_format(self) -> None:
        violations = [make_violation()]
        output = format_violations(violations, fmt="text")
        assert "test.py:1:0" in output
        assert "DOCSTRING_REMOVED" in output
