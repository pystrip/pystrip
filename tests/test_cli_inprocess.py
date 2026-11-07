"""In-process CLI tests.

These complement the end-to-end subprocess tests in ``test_cli.py`` by calling
``pystrip.cli.main`` directly. They run faster, are easier to debug, and let the
coverage tooling see the CLI code paths that a child process would hide.

Each test changes into a ``tmp_path`` with no project markers, so configuration
discovery resolves to built-in defaults (``jobs = 1``) instead of picking up the
repository's own ``[tool.pystrip]`` table.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pystrip import cli


def run_cli(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Invoke ``cli.main`` with ``argv`` and return the process exit code."""
    monkeypatch.setattr("sys.argv", ["pystrip", *argv])
    try:
        cli.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def test_check_reports_changes_with_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text("# comment\nx = 1\n", encoding="utf-8")

    code = run_cli([str(tmp_path / "m.py"), "--check"], monkeypatch)

    assert code == 1
    assert "Would change" in capsys.readouterr().err


def test_clean_file_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")

    code = run_cli([str(tmp_path / "clean.py"), "--check"], monkeypatch)

    assert code == 0
    assert "All files clean." in capsys.readouterr().err


def test_in_place_rewrites_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "m.py"
    target.write_text("# comment\nx = 1  # trailing\n", encoding="utf-8")

    code = run_cli([str(target), "--in-place"], monkeypatch)

    assert code == 0
    assert "#" not in target.read_text(encoding="utf-8")


def test_output_dir_leaves_input_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "m.py"
    original = "# comment\nx = 1\n"
    src.write_text(original, encoding="utf-8")
    out_dir = tmp_path / "out"

    code = run_cli([str(src), "--output-dir", str(out_dir)], monkeypatch)

    assert code == 0
    assert src.read_text(encoding="utf-8") == original
    assert "#" not in (out_dir / "m.py").read_text(encoding="utf-8")


def test_json_format_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text('"""doc."""\nx = 1\n', encoding="utf-8")

    code = run_cli([str(tmp_path / "m.py"), "--check", "--format", "json"], monkeypatch)

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["docstrings_removed"] == 1


def test_no_python_files_found_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    code = run_cli([str(tmp_path), "--check"], monkeypatch)

    assert code == 0
    assert "No Python files found." in capsys.readouterr().err


def test_config_error_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    bad = tmp_path / "bad.toml"
    bad.write_text("jobs = -1\n", encoding="utf-8")
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")

    code = run_cli([str(tmp_path / "m.py"), "--config", str(bad)], monkeypatch)

    assert code == 2


def test_stdin_writes_stripped_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _FakeStdin("# c\nx = 1\n"))

    code = run_cli(["-"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == "x = 1\n"


def test_stdin_rejects_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _FakeStdin("x = 1\n"))

    code = run_cli(["-", "--in-place"], monkeypatch)

    assert code == 2


class _FakeStdin:
    def __init__(self, data: str) -> None:
        self._data = data

    def read(self) -> str:
        return self._data
