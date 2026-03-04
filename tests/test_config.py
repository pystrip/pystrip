"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from pystrip.config import load_config


def test_default_config(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.remove_comments is True
    assert cfg.remove_docstrings is True
    assert cfg.jobs == 1
    assert cfg.cache is True


def test_load_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.pystrip]
remove_comments = false
jobs = 4
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.remove_comments is False
    assert cfg.jobs == 4


def test_load_from_standalone(tmp_path: Path) -> None:
    standalone = tmp_path / ".pystrip.toml"
    standalone.write_text(
        """
[pystrip]
remove_docstrings = false
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.remove_docstrings is False


def test_standalone_overrides_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.pystrip]
remove_comments = false
jobs = 2
""",
        encoding="utf-8",
    )
    standalone = tmp_path / ".pystrip.toml"
    standalone.write_text(
        """
[pystrip]
remove_comments = true
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.remove_comments is True
    assert cfg.jobs == 2  # from pyproject still


def test_explicit_config_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom.toml"
    custom.write_text(
        """
[pystrip]
jobs = 8
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path, config_path=custom)
    assert cfg.jobs == 8
