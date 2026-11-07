"""Unit tests for project-root discovery."""

from __future__ import annotations

from pathlib import Path

from pystrip.discovery import find_project_root


def test_finds_directory_containing_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)

    assert find_project_root(nested) == tmp_path.resolve()


def test_finds_directory_containing_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    assert find_project_root(nested) == tmp_path.resolve()


def test_falls_back_to_start_when_no_marker(tmp_path: Path) -> None:
    nested = tmp_path / "x"
    nested.mkdir()

    assert find_project_root(nested) == nested.resolve()


def test_start_directory_marker_wins_over_parents(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    child = tmp_path / "child"
    child.mkdir()
    (child / "pyproject.toml").write_text("", encoding="utf-8")

    assert find_project_root(child) == child.resolve()
