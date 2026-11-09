"""In-process CLI tests for the 1.5 feature set.

Same harness as ``test_cli_inprocess.py``: each test runs inside a ``tmp_path``
with no project markers so only built-in defaults apply.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from pystrip import cli
from pystrip.utils import collect_python_files, git_ignored


def run_cli(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr("sys.argv", ["pystrip", *argv])
    try:
        cli.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def feed_stdin(text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


def one_cell(source: str) -> dict[str, object]:
    return {"cell_type": "code", "metadata": {}, "outputs": [], "source": [source]}


# --- select / ignore -------------------------------------------------------


def test_select_limits_to_listed_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin('# c\n"""d"""\nx: int = 1\n', monkeypatch)

    code = run_cli(["-", "--select", "DOCSTRING_REMOVED"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == "# c\nx: int = 1\n"


def test_ignore_is_comma_separated_and_case_insensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin('# c\n"""d"""\nx: int = 1\n', monkeypatch)

    code = run_cli(["-", "--ignore", "comment_removed,DOCSTRING_REMOVED"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == '# c\n"""d"""\nx = 1\n'


def test_keep_flags_still_win_over_select(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin("# c\nx = 1\n", monkeypatch)

    code = run_cli(["-", "--select", "ALL", "--keep-comments"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == "# c\nx = 1\n"


def test_unknown_rule_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin("x = 1\n", monkeypatch)

    code = run_cli(["-", "--select", "BOGUS"], monkeypatch)

    assert code == 2
    assert "Unknown rule 'BOGUS'" in capsys.readouterr().err


# --- --stdin-filename --------------------------------------------------------


def test_stdin_filename_is_reported_in_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin("# c\nx = 1\n", monkeypatch)

    argv = ["-", "--check", "--stdin-filename", "src/app.py", "--format", "json"]
    code = run_cli(argv, monkeypatch)

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["violations"][0]["file"] == "src/app.py"


def test_stdin_filename_selects_stub_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin("x: int  # c\n", monkeypatch)

    code = run_cli(["-", "--stdin-filename", "pkg/mod.pyi"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == "x: int\n"


def test_stdin_filename_selects_notebook_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    nb = {"cells": [one_cell("x = 1  # c\n")]}
    feed_stdin(json.dumps(nb), monkeypatch)

    code = run_cli(["-", "--stdin-filename", "nb.ipynb"], monkeypatch)

    assert code == 0
    assert json.loads(capsys.readouterr().out)["cells"][0]["source"] == ["x = 1\n"]


def test_stdin_filename_requires_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")

    code = run_cli(["m.py", "--stdin-filename", "m.py"], monkeypatch)

    assert code == 2
    assert "--stdin-filename requires '-'" in capsys.readouterr().err


# --- --keep-header -------------------------------------------------------------


def test_keep_header_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    feed_stdin("# Copyright\n# MIT\n\n# gone\nx = 1\n", monkeypatch)

    code = run_cli(["-", "--keep-header"], monkeypatch)

    assert code == 0
    assert capsys.readouterr().out == "# Copyright\n# MIT\n\nx = 1\n"


# --- file discovery: .pyi, .ipynb, .gitignore --------------------------------------


def test_directories_yield_py_pyi_and_ipynb(tmp_path: Path) -> None:
    for name in ("a.py", "b.pyi", "c.ipynb", "d.txt", "e.pyc"):
        (tmp_path / name).write_text("", encoding="utf-8")

    found = collect_python_files([tmp_path])

    assert [p.name for p in found] == ["a.py", "b.pyi", "c.ipynb"]


def test_explicit_file_of_other_suffix_is_ignored(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("", encoding="utf-8")
    assert collect_python_files([other]) == []


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "gen.py").write_text("# c\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("# c\n", encoding="utf-8")
    return tmp_path


def test_gitignored_files_kept_by_default(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(git_repo)
    found = collect_python_files([Path(".")])
    assert Path("build/gen.py") in found


def test_respect_gitignore_drops_ignored_files(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(git_repo)
    found = collect_python_files([Path(".")], respect_gitignore=True)
    assert found == [Path("src.py")]


def test_explicit_path_beats_gitignore(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(git_repo)
    found = collect_python_files([Path("build/gen.py")], respect_gitignore=True)
    assert found == [Path("build/gen.py")]


def test_git_ignored_outside_repository_ignores_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert git_ignored([Path("a.py")]) == set()


def test_git_ignored_without_git_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)
    assert git_ignored([Path("a.py")]) == set()


def test_respect_gitignore_cli_flag(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(git_repo)

    code = run_cli([".", "--check", "--respect-gitignore", "--format", "json"], monkeypatch)

    assert code == 1
    files = {v["file"] for v in json.loads(capsys.readouterr().out)["violations"]}
    assert files == {"src.py"}


# --- notebooks through the CLI ----------------------------------------------------------


def test_notebook_in_place_and_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    nb = {"cells": [one_cell("x = 1  # c\n")]}
    path = tmp_path / "nb.ipynb"
    path.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")

    code = run_cli(["nb.ipynb", "--in-place", "--diff", "--quiet"], monkeypatch)

    assert code == 0
    assert '-    "x = 1  # c\\n"' in capsys.readouterr().out
    assert json.loads(path.read_text(encoding="utf-8"))["cells"][0]["source"] == ["x = 1\n"]


def test_skipped_file_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text("# pystrip: skip-file\n# c\nx = 1\n", encoding="utf-8")

    code = run_cli(["m.py", "--check"], monkeypatch)

    assert code == 0
    assert "All files clean" in capsys.readouterr().err
