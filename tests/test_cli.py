"""Tests for CLI behavior."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pystrip.cli import _apply_cli_overrides, _build_parser
from pystrip.config import PyStripConfig


def test_check_mode_exit_code(tmp_path: Path) -> None:
    """--check mode should exit 1 when changes would occur."""
    py_file = tmp_path / "test.py"
    py_file.write_text('"""Module docstring."""\n\nx = 1\n', encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--check"],
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
        [sys.executable, "-m", "pystrip", str(py_file), "--check"],
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


def test_cli_override_keep_comments() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--keep-comments", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.remove_comments is False


def test_cli_override_keep_blank() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--keep-blank", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.remove_blank_lines is False


def test_cli_override_keep_type_annotations() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--keep-type-annotations", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.remove_type_annotations is False


def test_no_recursive_flag_parses() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--no-recursive", "."])
    assert args.recursive is False


def test_recursive_flag_removed() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--recursive", "."])


def test_old_blank_flag_removed() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--no-remove-blank-lines", "."])


def test_no_cache_flag_removed() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--no-cache", "."])


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
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert isinstance(data["violations"], list)
    assert data["violations"][0]["rule"] == "DOCSTRING_REMOVED"
    assert data["summary"]["docstrings_removed"] >= 1


def test_verbose_prints_removed_comments_with_locations(tmp_path: Path) -> None:
    py_file = tmp_path / "verbose_comments.py"
    py_file.write_text("# one\nx = 1  # two\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pystrip",
            str(py_file),
            "--check",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "verbose_comments.py:1:" in result.stderr
    assert "verbose_comments.py:2:" in result.stderr
    assert "removed 2 comment(s)." in result.stderr


def test_in_place_writes_after_check_run(tmp_path: Path) -> None:
    py_file = tmp_path / "in_place_after_check.py"
    py_file.write_text('"""Docstring."""\n# note\nx = 1\n', encoding="utf-8")

    import subprocess

    first = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--check"],
        capture_output=True,
        text=True,
    )
    assert first.returncode == 1

    second = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--in-place"],
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0

    updated = py_file.read_text(encoding="utf-8")
    assert '"""Docstring."""' not in updated
    assert "# note" not in updated


def test_summary_includes_docstring_and_comment_counts(tmp_path: Path) -> None:
    py_file = tmp_path / "summary_counts.py"
    py_file.write_text('"""Docstring."""\n# note\nx = 1\n', encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--check"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "1 docstring(s)" in result.stderr
    assert "1 comment(s)" in result.stderr


def test_cli_override_remove_shebang() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--remove-shebang", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.remove_shebang is True


def test_cli_override_use_pass() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--use-pass", "."])
    cfg = PyStripConfig()
    _apply_cli_overrides(cfg, args)
    assert cfg.use_pass is True


def test_continue_on_error_flag_parses() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--continue-on-error", "."])
    assert args.continue_on_error is True


def test_shebang_preserved_by_default(tmp_path: Path) -> None:
    """Shebang lines should be kept by default even with --in-place."""
    py_file = tmp_path / "shebang.py"
    py_file.write_text("#!/usr/bin/env python3\n# comment\nx = 1\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pystrip", str(py_file), "--in-place"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    updated = py_file.read_text(encoding="utf-8")
    assert "#!/usr/bin/env python3" in updated
    assert "# comment" not in updated


def test_invalid_config_exits_2_with_error_message(tmp_path: Path) -> None:
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    bad_cfg = tmp_path / "bad.toml"
    bad_cfg.write_text(
        """
[pystrip]
jobs = "many"
""",
        encoding="utf-8",
    )

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pystrip",
            str(py_file),
            "--config",
            str(bad_cfg),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Invalid 'jobs'" in result.stderr


def test_continue_on_error_processes_remaining_files(tmp_path: Path) -> None:
    valid = tmp_path / "valid.py"
    valid.write_text('"""Doc."""\nx = 1\n', encoding="utf-8")

    broken = tmp_path / "broken.py"
    broken.write_text("def oops(:\n    pass\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pystrip",
            str(valid),
            str(broken),
            "--check",
            "--continue-on-error",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "DOCSTRING_REMOVED" in result.stdout
    assert "Failed to parse" in result.stderr


def test_stdin_mode_writes_stripped_code_to_stdout() -> None:
    import subprocess

    source = '"""Doc."""\n# note\nx = 1  # trailing\n'
    result = subprocess.run(
        [sys.executable, "-m", "pystrip", "-"],
        input=source,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "x = 1\n"
    assert "Changed 1 file(s)" in result.stderr


def test_stdin_mode_check_outputs_violations() -> None:
    import subprocess

    source = '"""Doc."""\nx = 1\n'
    result = subprocess.run(
        [sys.executable, "-m", "pystrip", "-", "--check"],
        input=source,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "DOCSTRING_REMOVED" in result.stdout
    assert "Would change 1 file(s)" in result.stderr


def test_stdin_mode_rejects_in_place() -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pystrip", "-", "--in-place"],
        input="x = 1\n",
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--in-place cannot be used with stdin input" in result.stderr
