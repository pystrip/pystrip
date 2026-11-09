"""Utility functions for pystrip."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

#: File suffixes pystrip knows how to strip.
SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".py", ".pyi", ".ipynb"})


def collect_python_files(
    paths: list[Path],
    recursive: bool = True,
    exclude: list[str] | None = None,
    exclude_glob: list[str] | None = None,
    respect_gitignore: bool = False,
) -> list[Path]:
    """Collect Python source files (``.py``, ``.pyi``, ``.ipynb``) from paths.

    Args:
        paths: Directories or files to search.
        recursive: Whether to search directories recursively.
        exclude: Path prefixes/fragments to exclude.
        exclude_glob: Glob patterns to exclude.
        respect_gitignore: Drop files that ``git`` ignores. A file given
            explicitly on the command line is always kept.

    Returns:
        Sorted list of file paths.
    """
    exclude = exclude or []
    exclude_glob = exclude_glob or []
    result: list[Path] = []
    explicit: set[Path] = set()

    for path in paths:
        if path.is_file():
            if path.suffix in SUPPORTED_SUFFIXES:
                result.append(path)
                explicit.add(path)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            for candidate in path.glob(pattern):
                if candidate.suffix in SUPPORTED_SUFFIXES and candidate.is_file():
                    result.append(candidate)

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

    if respect_gitignore and filtered:
        ignored = git_ignored(filtered)
        filtered = [f for f in filtered if f in explicit or f not in ignored]

    return sorted(set(filtered))


def git_ignored(files: list[Path]) -> set[Path]:
    """Return the subset of ``files`` that git ignores.

    Uses ``git check-ignore`` so the full ignore stack applies (nested
    ``.gitignore`` files, ``.git/info/exclude``, the global excludes file).
    Outside a repository, or without ``git`` on ``PATH``, nothing is ignored.
    """
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-z", "--stdin"],
            input="\0".join(str(f) for f in files),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return set()
    # 0: some paths ignored, 1: none ignored, 128: not a repository.
    if proc.returncode not in (0, 1):
        return set()
    return {Path(p) for p in proc.stdout.split("\0") if p}
