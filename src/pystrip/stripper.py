"""Core stripping logic for pystrip."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

import libcst as cst
from libcst.metadata import MetadataWrapper

#: Every rule pystrip can report, in the order ``--select`` lists them.
RULES: tuple[str, ...] = ("COMMENT_REMOVED", "DOCSTRING_REMOVED", "TYPE_ANNOTATION_REMOVED")

#: ``# pystrip: skip-file`` on its own comment line anywhere in the file leaves
#: the whole file untouched.
_SKIP_FILE_RE = re.compile(r"^\s*#\s*pystrip:\s*skip-file\b", re.MULTILINE)

#: A comment line that is part of the leading header block: shebang, encoding
#: cookie, license banner. Only matched from line 1 while lines keep matching.
_HEADER_LINE_RE = re.compile(r"^\s*#")


@dataclass
class Violation:
    """A single violation found during stripping."""

    file: str
    line: int
    column: int
    rule: str  # one of RULES
    message: str


@dataclass
class StripConfig:
    """Configuration for a single strip operation."""

    remove_comments: bool = True
    remove_docstrings: bool = True
    remove_blank_lines: bool = True
    remove_type_annotations: bool = True
    remove_shebang: bool = False
    use_pass: bool = False
    keep_header: bool = False
    filename: str = "<unknown>"


@dataclass
class StripResult:
    """Result of a strip operation."""

    modified_code: str
    changed: bool
    violations: list[Violation] = field(default_factory=list)
    skipped: bool = False


def has_skip_file_pragma(source: str) -> bool:
    """Return True if ``source`` opts out of stripping with ``# pystrip: skip-file``."""
    return _SKIP_FILE_RE.search(source) is not None


def header_end_line(source: str) -> int:
    """Return the 1-based last line of the leading comment block, or 0 if none.

    The header is the run of comment lines that starts on line 1 and stops at
    the first blank or non-comment line. That is the shape of a shebang,
    encoding cookie, or license banner, which is what ``--keep-header`` exists
    to protect.
    """
    end = 0
    for lineno, line in enumerate(source.splitlines(), start=1):
        if not _HEADER_LINE_RE.match(line):
            break
        end = lineno
    return end


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

    if has_skip_file_pragma(source):
        return StripResult(modified_code=source, changed=False, skipped=True)

    if config.filename.endswith(".pyi") and config.remove_type_annotations:
        # Annotations are the whole point of a stub file.
        config = replace(config, remove_type_annotations=False)

    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ValueError(f"Failed to parse {config.filename}: {exc}") from exc

    wrapper = MetadataWrapper(tree)
    transformer = PyStripTransformer(
        config=config,
        filename=config.filename,
        header_end=header_end_line(source) if config.keep_header else 0,
    )
    new_tree = wrapper.visit(transformer)
    modified_code = new_tree.code

    return StripResult(
        modified_code=modified_code,
        changed=modified_code != source,
        violations=transformer.violations,
    )
