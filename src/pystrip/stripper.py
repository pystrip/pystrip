"""Core stripping logic for pystrip."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper

if TYPE_CHECKING:
    pass


@dataclass
class Violation:
    """A single violation found during stripping."""

    file: str
    line: int
    column: int
    rule: str  # "COMMENT_REMOVED" or "DOCSTRING_REMOVED"
    message: str


@dataclass
class StripConfig:
    """Configuration for a single strip operation."""

    remove_comments: bool = True
    remove_docstrings: bool = True
    remove_blank_lines: bool = True
    remove_type_annotations: bool = True
    filename: str = "<unknown>"


@dataclass
class StripResult:
    """Result of a strip operation."""

    modified_code: str
    changed: bool
    violations: list[Violation] = field(default_factory=list)


def strip_code(source: str, config: StripConfig) -> StripResult:
    """Strip comments and/or docstrings from Python source code.

    Args:
        source: Python source code as a string.
        config: Configuration controlling what to remove.

    Returns:
        StripResult with modified code, changed flag, and violations.
    """
    # Import here to avoid circular imports
    from pystrip.visitor import PyStripTransformer

    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ValueError(f"Failed to parse {config.filename}: {exc}") from exc

    wrapper = MetadataWrapper(tree)
    transformer = PyStripTransformer(config=config, filename=config.filename)
    new_tree = wrapper.visit(transformer)
    modified_code = new_tree.code

    return StripResult(
        modified_code=modified_code,
        changed=modified_code != source,
        violations=transformer.violations,
    )
