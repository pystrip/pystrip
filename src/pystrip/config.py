"""Configuration loading for pystrip."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a pystrip configuration file is invalid."""


@dataclass
class PyStripConfig:
    """Resolved configuration for a pystrip run."""

    remove_comments: bool = True
    remove_docstrings: bool = True
    remove_blank_lines: bool = True
    remove_type_annotations: bool = True
    remove_shebang: bool = False
    use_pass: bool = False
    exclude: list[str] = field(default_factory=list)
    exclude_glob: list[str] = field(default_factory=list)
    line_length: int = 100
    jobs: int = 1
    config_path: Path | None = None


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Failed to read config file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid TOML document in {path}: expected table at root")
    return data


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
        data = _load_toml(pyproject_path)
        tool = data.get("tool", {})
        if not isinstance(tool, dict):
            raise ConfigError(f"Invalid [tool] table in {pyproject_path}: expected table")
        section = tool.get("pystrip", {})
        if section and not isinstance(section, dict):
            raise ConfigError(f"Invalid [tool.pystrip] table in {pyproject_path}: expected table")
        _apply_section(cfg, section, source=pyproject_path)

    # Try .pystrip.toml (overrides pyproject.toml)
    standalone_path = project_root / ".pystrip.toml"
    if standalone_path.exists():
        data = _load_toml(standalone_path)
        section = data.get("pystrip", data)
        if not isinstance(section, dict):
            raise ConfigError(f"Invalid [pystrip] table in {standalone_path}: expected table")
        _apply_section(cfg, section, source=standalone_path)

    # Explicit --config overrides everything
    if config_path is not None:
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
        data = _load_toml(config_path)
        section = data.get("pystrip", data)
        if not isinstance(section, dict):
            raise ConfigError(f"Invalid [pystrip] table in {config_path}: expected table")
        _apply_section(cfg, section, source=config_path)
        cfg.config_path = config_path

    return cfg


def _require_bool(section: dict[str, Any], key: str, source: Path) -> bool:
    value = section[key]
    if not isinstance(value, bool):
        raise ConfigError(f"Invalid '{key}' in {source}: expected bool, got {type(value).__name__}")
    return value


def _require_int(section: dict[str, Any], key: str, source: Path) -> int:
    value = section[key]
    if not isinstance(value, int):
        raise ConfigError(f"Invalid '{key}' in {source}: expected int, got {type(value).__name__}")
    return value


def _require_str_list(section: dict[str, Any], key: str, source: Path) -> list[str]:
    value = section[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"Invalid '{key}' in {source}: expected list[str]")
    return value


def _apply_section(cfg: PyStripConfig, section: dict[str, Any], source: Path) -> None:
    if "remove_comments" in section:
        cfg.remove_comments = _require_bool(section, "remove_comments", source)
    if "remove_docstrings" in section:
        cfg.remove_docstrings = _require_bool(section, "remove_docstrings", source)
    if "remove_blank_lines" in section:
        cfg.remove_blank_lines = _require_bool(section, "remove_blank_lines", source)
    if "remove_type_annotations" in section:
        cfg.remove_type_annotations = _require_bool(section, "remove_type_annotations", source)
    if "remove_shebang" in section:
        cfg.remove_shebang = _require_bool(section, "remove_shebang", source)
    if "use_pass" in section:
        cfg.use_pass = _require_bool(section, "use_pass", source)
    if "exclude" in section:
        cfg.exclude = _require_str_list(section, "exclude", source)
    if "exclude_glob" in section:
        cfg.exclude_glob = _require_str_list(section, "exclude_glob", source)
    if "line_length" in section:
        line_length = _require_int(section, "line_length", source)
        if line_length <= 0:
            raise ConfigError(f"Invalid 'line_length' in {source}: expected > 0")
        cfg.line_length = line_length
    if "jobs" in section:
        jobs = _require_int(section, "jobs", source)
        if jobs <= 0:
            raise ConfigError(f"Invalid 'jobs' in {source}: expected > 0")
        cfg.jobs = jobs
