"""Tests for Jupyter notebook stripping."""

from __future__ import annotations

import json
from typing import Any

import pytest

from pystrip.notebook import strip_notebook
from pystrip.stripper import StripConfig


def code_cell(*lines: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "outputs": [{"output_type": "stream", "name": "stdout", "text": ["# not code\n"]}],
        "source": list(lines),
    }


def markdown_cell(*lines: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": list(lines)}


def notebook(*cells: dict[str, Any]) -> str:
    nb = {"cells": list(cells), "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n"


def sources(text: str) -> list[list[str]]:
    return [cell["source"] for cell in json.loads(text)["cells"]]


def test_strips_code_cells_only() -> None:
    text = notebook(
        code_cell("# comment\n", "def f(x: int) -> int:\n", '    """Doc."""\n', "    return x\n"),
        markdown_cell("# Heading stays\n"),
    )
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))

    assert result.changed is True
    assert sources(result.modified_code) == [
        ["def f(x):\n", "    return x\n"],
        ["# Heading stays\n"],
    ]
    assert {v.rule for v in result.violations} == {
        "COMMENT_REMOVED",
        "DOCSTRING_REMOVED",
        "TYPE_ANNOTATION_REMOVED",
    }
    assert all(v.file == "nb.ipynb#cell0" for v in result.violations)


def test_outputs_and_metadata_untouched() -> None:
    text = notebook(code_cell("x = 1  # c\n"))
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))
    cell = json.loads(result.modified_code)["cells"][0]
    assert cell["outputs"] == [
        {"output_type": "stream", "name": "stdout", "text": ["# not code\n"]}
    ]
    assert cell["execution_count"] == 1


def test_round_trip_is_stable_when_nothing_changes() -> None:
    text = notebook(code_cell("x = 1\n"), markdown_cell("# md\n"))
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))
    assert result.changed is False
    assert result.modified_code == text


def test_line_magics_and_shell_escapes_survive() -> None:
    text = notebook(
        code_cell("%matplotlib inline\n", "# gone\n", "!pip install x  # gone too\n", "y = 1\n")
    )
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))
    assert sources(result.modified_code) == [
        ["%matplotlib inline\n", "!pip install x  # gone too\n", "y = 1\n"]
    ]


def test_cell_magic_cell_is_left_alone() -> None:
    text = notebook(code_cell("%%time\n", "# kept, not python\n", "x = 1\n"))
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))
    assert result.changed is False


def test_cell_with_skip_file_pragma_is_left_alone() -> None:
    text = notebook(code_cell("# pystrip: skip-file\n", "# kept\n", "x = 1\n"), code_cell("# c\n"))
    result = strip_notebook(text, StripConfig(filename="nb.ipynb"))
    assert sources(result.modified_code)[0] == ["# pystrip: skip-file\n", "# kept\n", "x = 1\n"]
    assert sources(result.modified_code)[1] == []


def test_string_source_is_accepted() -> None:
    nb = {"cells": [{"cell_type": "code", "metadata": {}, "outputs": [], "source": "x = 1  # c"}]}
    result = strip_notebook(json.dumps(nb), StripConfig(filename="nb.ipynb"))
    assert sources(result.modified_code) == [["x = 1"]]


def test_parse_error_names_the_cell() -> None:
    text = notebook(code_cell("x = 1\n"), code_cell("def broken(:\n"))
    with pytest.raises(ValueError, match="nb.ipynb#cell1"):
        strip_notebook(text, StripConfig(filename="nb.ipynb"))


@pytest.mark.parametrize("text", ["not json", "[]", '{"cells": 3}'])
def test_invalid_notebook_raises(text: str) -> None:
    with pytest.raises(ValueError, match="Failed to parse nb.ipynb"):
        strip_notebook(text, StripConfig(filename="nb.ipynb"))
