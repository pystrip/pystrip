"""Project root discovery for pystrip."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward from start, stopping at the first directory containing
    pyproject.toml or .git.

    Falls back to start directory itself if nothing found.
    """
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        if (directory / "pyproject.toml").exists() or (directory / ".git").exists():
            return directory
    return current
