"""Tests for CLI behavior."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pystrip.cli import _build_parser, _apply_cli_overrides
from pystrip.config import PyStripConfig


def test_check_mode_exit_code(tmp_path: Path) -> None:
    """--check mode should exit 1 when changes would occur."""
    py_file = tmp_path / "test.py"
    py_file.write_text('"""Module docstring."""\n\nx = 1\n', encoding="utf-8")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--check", "--no-cache"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_check_mode_clean_exit(tmp_path: Path) -> None:
    """--check mode should exit 0 when no changes needed."""
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--check", "--no-cache"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_cli_override_keep_docstrings() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--keep-docstrings", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.remove_docstrings is False


def test_json_output(tmp_path: Path) -> None:
    py_file = tmp_path / "test.py"
    py_file.write_text('"""Docstring."""\nx = 1\n', encoding="utf-8")

    import subprocess
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pystrip",
            str(py_file),
            "--check",
            "--format",
            "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert data[0]["rule"] == "DOCSTRING_REMOVED"
