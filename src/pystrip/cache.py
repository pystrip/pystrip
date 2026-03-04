"""File-based caching for pystrip."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CacheEntry:
    """Cached result for a single file."""

    sha256: str
    changed: bool
    violations: list[dict[str, str | int]]


class StripCache:
    """Manages a cache of file hashes and results in <project_root>/.pystrip_cache/."""

    def __init__(self, project_root: Path) -> None:
        self._cache_dir = project_root / ".pystrip_cache"
        self._cache_dir.mkdir(exist_ok=True)

    def _cache_file(self, path: Path) -> Path:
        key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
        return self._cache_dir / f"{key}.json"

    def _file_hash(self, path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def is_unchanged(self, path: Path) -> bool:
        """Return True if the file hasn't changed since last cache write."""
        cache_file = self._cache_file(path)
        if not cache_file.exists():
            return False
        try:
            entry = json.loads(cache_file.read_text(encoding="utf-8"))
            return entry.get("sha256") == self._file_hash(path)
        except (json.JSONDecodeError, KeyError, OSError):
            return False

    def write(self, path: Path, entry: CacheEntry) -> None:
        cache_file = self._cache_file(path)
        cache_file.write_text(
            json.dumps(asdict(entry), indent=2),
            encoding="utf-8",
        )

    def read(self, path: Path) -> CacheEntry | None:
        cache_file = self._cache_file(path)
        if not cache_file.exists():
            return None
        try:
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            return CacheEntry(
                sha256=raw["sha256"],
                changed=raw["changed"],
                violations=raw["violations"],
            )
        except (json.JSONDecodeError, KeyError, OSError):
            return None
