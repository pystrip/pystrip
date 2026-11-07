"""Unit tests for file collection in pystrip.utils."""

from __future__ import annotations

from pathlib import Path

from pystrip.utils import collect_python_files


def _touch(path: Path, content: str = "x = 1\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_collects_only_python_files(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "b.txt", "not python")
    _touch(tmp_path / "c.py")

    found = collect_python_files([tmp_path])

    assert found == sorted([tmp_path / "a.py", tmp_path / "c.py"])


def test_recursive_descends_into_subdirectories(tmp_path: Path) -> None:
    _touch(tmp_path / "top.py")
    _touch(tmp_path / "pkg" / "nested.py")

    found = collect_python_files([tmp_path], recursive=True)

    assert tmp_path / "pkg" / "nested.py" in found
    assert tmp_path / "top.py" in found


def test_non_recursive_skips_subdirectories(tmp_path: Path) -> None:
    _touch(tmp_path / "top.py")
    _touch(tmp_path / "pkg" / "nested.py")

    found = collect_python_files([tmp_path], recursive=False)

    assert found == [tmp_path / "top.py"]


def test_explicit_file_path_is_collected(tmp_path: Path) -> None:
    target = _touch(tmp_path / "only.py")

    assert collect_python_files([target]) == [target]


def test_explicit_non_python_file_is_ignored(tmp_path: Path) -> None:
    target = _touch(tmp_path / "data.json", "{}")

    assert collect_python_files([target]) == []


def test_exclude_matches_path_fragment(tmp_path: Path) -> None:
    _touch(tmp_path / "keep.py")
    _touch(tmp_path / "tests" / "test_x.py")

    found = collect_python_files([tmp_path], exclude=["tests/"])

    assert found == [tmp_path / "keep.py"]


def test_exclude_glob_matches_file_name(tmp_path: Path) -> None:
    _touch(tmp_path / "keep.py")
    _touch(tmp_path / "models.generated.py")

    found = collect_python_files([tmp_path], exclude_glob=["*.generated.py"])

    assert found == [tmp_path / "keep.py"]


def test_results_are_sorted_and_deduplicated(tmp_path: Path) -> None:
    a = _touch(tmp_path / "a.py")
    b = _touch(tmp_path / "b.py")

    # Pass the directory and an explicit file so the same path appears twice.
    found = collect_python_files([tmp_path, a])

    assert found == sorted([a, b])


def test_missing_path_yields_nothing(tmp_path: Path) -> None:
    assert collect_python_files([tmp_path / "does-not-exist.py"]) == []
