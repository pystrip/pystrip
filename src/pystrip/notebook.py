"""Jupyter notebook (``.ipynb``) support.

A notebook is JSON; only the ``source`` of its code cells is Python. Each code
cell is stripped on its own, so a parse error in one cell is reported with the
cell index and the rest of the file is untouched. Markdown cells and outputs
are never modified.

IPython line magics (``%matplotlib inline``) and shell escapes (``!pip ...``)
are not Python, so they are swapped for placeholder assignments before parsing
and restored afterwards. Cell magics (``%%time``) make the whole cell
non-Python and leave it unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Any

from pystrip.stripper import StripConfig, StripResult, Violation, strip_code

_MAGIC_RE = re.compile(r"^(\s*)([%!?].*)$")
_PLACEHOLDER = "__pystrip_magic_{index}__ = None"
_PLACEHOLDER_RE = re.compile(r"^(\s*)__pystrip_magic_(\d+)__ = None$")

#: Indentation used by Jupyter itself, so a round trip is a no-op diff.
_JSON_INDENT = 1


def _cell_source(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def _split_source(text: str) -> list[str]:
    """Return ``text`` in the list-of-lines form nbformat uses."""
    return text.splitlines(keepends=True)


def _mask_magics(source: str) -> tuple[str, dict[int, str]]:
    masked: list[str] = []
    magics: dict[int, str] = {}
    for line in source.splitlines(keepends=True):
        match = _MAGIC_RE.match(line.rstrip("\r\n"))
        if match is None:
            masked.append(line)
            continue
        index = len(magics)
        magics[index] = match.group(2)
        newline = line[len(line.rstrip("\r\n")) :]
        masked.append(f"{match.group(1)}{_PLACEHOLDER.format(index=index)}{newline}")
    return "".join(masked), magics


def _unmask_magics(source: str, magics: dict[int, str]) -> str:
    if not magics:
        return source
    restored: list[str] = []
    for line in source.splitlines(keepends=True):
        match = _PLACEHOLDER_RE.match(line.rstrip("\r\n"))
        if match is None:
            restored.append(line)
            continue
        newline = line[len(line.rstrip("\r\n")) :]
        restored.append(f"{match.group(1)}{magics[int(match.group(2))]}{newline}")
    return "".join(restored)


def _is_cell_magic(source: str) -> bool:
    return source.lstrip().startswith("%%")


def strip_notebook(text: str, config: StripConfig) -> StripResult:
    """Strip every code cell of a notebook and return the re-serialised JSON.

    Raises:
        ValueError: if ``text`` is not a notebook, or a cell fails to parse.
    """
    try:
        notebook = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse {config.filename}: not valid JSON: {exc}") from exc
    cells = notebook.get("cells") if isinstance(notebook, dict) else None
    if not isinstance(cells, list):
        raise ValueError(f"Failed to parse {config.filename}: no 'cells' list in notebook")

    violations: list[Violation] = []
    changed = False
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = _cell_source(cell)
        if not source.strip() or _is_cell_magic(source):
            continue
        masked, magics = _mask_magics(source)
        cell_config = replace(config, filename=f"{config.filename}#cell{index}")
        result = strip_code(masked, cell_config)
        if result.skipped or not result.changed:
            continue
        stripped = _unmask_magics(result.modified_code, magics)
        # A cell that was only comments is now empty, not a lone newline.
        cell["source"] = _split_source(stripped) if stripped.strip() else []
        violations.extend(result.violations)
        changed = True

    if not changed:
        return StripResult(modified_code=text, changed=False, violations=violations)

    modified = json.dumps(notebook, indent=_JSON_INDENT, ensure_ascii=False)
    if text.endswith("\n"):
        modified += "\n"
    return StripResult(modified_code=modified, changed=True, violations=violations)
