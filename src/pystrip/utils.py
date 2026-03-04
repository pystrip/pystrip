"""Utility functions for pystrip."""

from __future__ import annotations

import fnmatch
from pathlib import Path


def collect_python_files(
    paths: list[Path],
    recursive: bool = True,
    exclude: list[str] | None = None,
    exclude_glob: list[str] | None = None,
) -> list[Path]:
    """Collect Python files from paths.

    Args:
        paths: Directories or files to search.
        recursive: Whether to search directories recursively.
        exclude: Path prefixes/fragments to exclude.
        exclude_glob: Glob patterns to exclude.

    Returns:
        Sorted list of .py file paths.
    """
    exclude = exclude or []
    exclude_glob = exclude_glob or []
    result: list[Path] = []

    for path in paths:
        if path.is_file():
            if path.suffix == ".py":
                result.append(path)
        elif path.is_dir():
            pattern = "**/*.py" if recursive else "*.py"
            for py_file in path.glob(pattern):
                result.append(py_file)

    filtered: list[Path] = []
    for py_file in result:
        py_str = str(py_file)
        skip = False
        for exc in exclude:
            if exc in py_str:
                skip = True
                break
        if not skip:
            for pat in exclude_glob:
                if fnmatch.fnmatch(py_file.name, pat):
                    skip = True
                    break
        if not skip:
            filtered.append(py_file)

    return sorted(set(filtered))
