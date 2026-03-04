"""Configuration loading for pystrip."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PyStripConfig:
    """Resolved configuration for a pystrip run."""

    remove_comments: bool = True
    remove_docstrings: bool = True
    exclude: list[str] = field(default_factory=list)
    exclude_glob: list[str] = field(default_factory=list)
    line_length: int = 100
    jobs: int = 1
    cache: bool = True
    config_path: Path | None = None


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_config(
    project_root: Path,
    config_path: Path | None = None,
) -> PyStripConfig:
    """Load configuration from files, using priority order.

    Priority:
    1. CLI arguments (applied separately by caller)
    2. Explicit --config path
    3. .pystrip.toml in project root
    4. pyproject.toml [tool.pystrip] in project root
    5. Internal defaults
    """
    cfg = PyStripConfig()

    # Try pyproject.toml first (lowest file priority)
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            data = _load_toml(pyproject_path)
            section = data.get("tool", {}).get("pystrip", {})
            _apply_section(cfg, section)
        except Exception:
            pass

    # Try .pystrip.toml (overrides pyproject.toml)
    standalone_path = project_root / ".pystrip.toml"
    if standalone_path.exists():
        try:
            data = _load_toml(standalone_path)
            section = data.get("pystrip", data)
            _apply_section(cfg, section)
        except Exception:
            pass

    # Explicit --config overrides everything
    if config_path is not None and config_path.exists():
        try:
            data = _load_toml(config_path)
            section = data.get("pystrip", data)
            _apply_section(cfg, section)
            cfg.config_path = config_path
        except Exception:
            pass

    return cfg


def _apply_section(cfg: PyStripConfig, section: dict[str, Any]) -> None:
    if "remove_comments" in section:
        cfg.remove_comments = bool(section["remove_comments"])
    if "remove_docstrings" in section:
        cfg.remove_docstrings = bool(section["remove_docstrings"])
    if "exclude" in section:
        cfg.exclude = list(section["exclude"])
    if "exclude_glob" in section:
        cfg.exclude_glob = list(section["exclude_glob"])
    if "line_length" in section:
        cfg.line_length = int(section["line_length"])
    if "jobs" in section:
        cfg.jobs = int(section["jobs"])
    if "cache" in section:
        cfg.cache = bool(section["cache"])
