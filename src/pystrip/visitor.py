"""libcst-based transformer for removing comments and docstrings."""

from __future__ import annotations

import re
from collections.abc import Sequence

import libcst as cst
from libcst import CSTTransformer
from libcst.metadata import PositionProvider

from pystrip.stripper import StripConfig, Violation

#: ``# pystrip: keep`` anywhere in a comment protects that comment, and, when
#: it trails a statement line, every removal on that line (docstring, annotation).
_KEEP_RE = re.compile(r"#\s*pystrip:\s*keep\b")


def _has_keep_pragma(comment: cst.Comment | None) -> bool:
    return comment is not None and _KEEP_RE.search(comment.value) is not None


def _line_has_keep_pragma(stmt: cst.BaseStatement) -> bool:
    """Return True if ``stmt`` is a simple statement line ending in ``# pystrip: keep``."""
    return isinstance(stmt, cst.SimpleStatementLine) and _has_keep_pragma(
        stmt.trailing_whitespace.comment
    )


def _is_docstring_node(node: cst.BaseStatement) -> bool:
    """Return True if node is a docstring (expression statement with a string literal).

    A docstring carrying a trailing ``# pystrip: keep`` is not reported as one,
    so every caller leaves it alone without a second check.
    """
    if not isinstance(node, cst.SimpleStatementLine):
        return False
    if len(node.body) != 1:
        return False
    if _line_has_keep_pragma(node):
        return False
    stmt = node.body[0]
    if not isinstance(stmt, cst.Expr):
        return False
    expr = stmt.value
    # Handle both SimpleString and ConcatenatedString / FormattedString
    return isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString))


def _is_annotation_only_line(stmt: cst.BaseStatement) -> bool:
    """Return True if stmt is a SimpleStatementLine containing only annotation-only AnnAssigns."""
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    if _line_has_keep_pragma(stmt):
        return False
    return bool(stmt.body) and all(
        isinstance(s, cst.AnnAssign) and s.value is None for s in stmt.body
    )


def _filter_annotation_only_lines(
    body: Sequence[cst.BaseStatement],
) -> list[cst.BaseStatement]:
    """Return body with annotation-only SimpleStatementLines removed."""
    return [stmt for stmt in body if not _is_annotation_only_line(stmt)]


def _make_empty_line() -> cst.EmptyLine:
    return cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))


class PyStripTransformer(CSTTransformer):
    """Removes comments and/or docstrings from a module."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self, config: StripConfig, filename: str = "<unknown>", header_end: int = 0
    ) -> None:
        super().__init__()
        self._config = config
        self._filename = filename
        self.violations: list[Violation] = []
        # Last physical line of the leading comment block protected by --keep-header.
        self._header_end = header_end
        # >0 while inside a statement line that trails a ``# pystrip: keep``.
        self._keep_depth = 0

    # ------------------------------------------------------------------
    # Comment removal
    # ------------------------------------------------------------------

    def _make_placeholder_stmt(self) -> cst.SimpleStatementLine:
        """Return a ``pass`` or ``...`` placeholder for an otherwise-empty body."""
        if self._config.use_pass:
            return cst.SimpleStatementLine(body=[cst.Pass()])
        return cst.SimpleStatementLine(body=[cst.Expr(value=cst.Ellipsis())])

    def _record_comment_removed(self, original_node: cst.CSTNode, message: str) -> None:
        pos = self.get_metadata(PositionProvider, original_node)
        self.violations.append(
            Violation(
                file=self._filename,
                line=pos.start.line,
                column=pos.start.column,
                rule="COMMENT_REMOVED",
                message=message,
            )
        )

    def leave_EmptyLine(
        self,
        original_node: cst.EmptyLine,
        updated_node: cst.EmptyLine,
    ) -> cst.EmptyLine | cst.RemovalSentinel:
        """Remove a standalone comment wherever libcst parked the line.

        ``EmptyLine`` is one of only two nodes that can hold a comment, so this
        covers every ``leading_lines`` / ``header`` / ``footer`` /
        ``lines_after_decorators`` / ``empty_lines`` sequence at once. Handling
        the node type instead of each statement type is what stops a comment
        position from being missed: there is no list of statements to keep up to
        date.
        """
        if not self._config.remove_comments or original_node.comment is None:
            return updated_node
        if _has_keep_pragma(original_node.comment):
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        # A shebang is a property of physical line 1, not of the "#!" prefix:
        # keeping any "#!" comment anywhere would make it an opt-out of the tool.
        if (
            original_node.comment.value.startswith("#!")
            and pos.start.line == 1
            and not self._config.remove_shebang
        ):
            return updated_node
        if pos.start.line <= self._header_end:
            return updated_node

        self._record_comment_removed(original_node, "Leading comment removed")
        if self._config.remove_blank_lines:
            return cst.RemoveFromParent()
        # --keep-blank: drop the comment but keep the physical line, so nothing
        # below it is renumbered.
        return updated_node.with_changes(comment=None)

    def leave_TrailingWhitespace(
        self,
        original_node: cst.TrailingWhitespace,
        updated_node: cst.TrailingWhitespace,
    ) -> cst.TrailingWhitespace:
        """Remove an end-of-line comment wherever it is attached.

        The second and last node type that can hold a comment. A trailing
        comment is never a shebang — a shebang has to start its line.
        """
        if not self._config.remove_comments or original_node.comment is None:
            return updated_node
        if _has_keep_pragma(original_node.comment):
            return updated_node

        self._record_comment_removed(original_node, "Trailing comment removed")
        return updated_node.with_changes(
            comment=None,
            whitespace=cst.SimpleWhitespace(""),
        )

    # ------------------------------------------------------------------
    # Module-level
    # ------------------------------------------------------------------

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self._config.remove_docstrings and updated_node.body:
            first = updated_node.body[0]
            if _is_docstring_node(first):
                # Use original node for metadata lookup (updated nodes are not in the map)
                orig_first = original_node.body[0]
                pos = self.get_metadata(PositionProvider, orig_first)
                self.violations.append(
                    Violation(
                        file=self._filename,
                        line=pos.start.line,
                        column=pos.start.column,
                        rule="DOCSTRING_REMOVED",
                        message="Module docstring removed",
                    )
                )
                # Replace with a pass if the module body would be empty, else remove
                remaining = list(updated_node.body[1:])
                if remaining:
                    updated_node = updated_node.with_changes(body=remaining)
                else:
                    updated_node = updated_node.with_changes(body=[self._make_placeholder_stmt()])

        if self._config.remove_type_annotations:
            new_body = _filter_annotation_only_lines(updated_node.body)
            if len(new_body) < len(updated_node.body):
                if new_body:
                    updated_node = updated_node.with_changes(body=new_body)
                else:
                    updated_node = updated_node.with_changes(body=[self._make_placeholder_stmt()])

        return updated_node

    # ------------------------------------------------------------------
    # Statement-level comment removal
    # ------------------------------------------------------------------

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:
        if _line_has_keep_pragma(node):
            self._keep_depth += 1
        return True

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if _line_has_keep_pragma(original_node):
            self._keep_depth -= 1
            return updated_node

        if self._config.remove_type_annotations:
            # For mixed lines (some annotation-only, some not), filter the annotation-only stmts.
            # Pure annotation-only lines are handled in leave_IndentedBlock / leave_Module.
            filtered = [
                s
                for s in updated_node.body
                if not (isinstance(s, cst.AnnAssign) and s.value is None)
            ]
            if 0 < len(filtered) < len(updated_node.body):
                updated_node = updated_node.with_changes(body=filtered)

        return updated_node

    # ------------------------------------------------------------------
    # Docstring removal from class / function bodies
    # ------------------------------------------------------------------

    def _remove_docstring_from_body(
        self, body: cst.BaseSuite, original_body: cst.BaseSuite, context: str
    ) -> cst.BaseSuite:
        if not isinstance(body, cst.IndentedBlock):
            return body
        stmts = list(body.body)
        if not stmts:
            return body
        first = stmts[0]
        if not _is_docstring_node(first):
            return body

        # Use original body node for metadata lookup (updated nodes not in the map)
        orig_stmts = (
            list(original_body.body) if isinstance(original_body, cst.IndentedBlock) else stmts
        )
        orig_first = orig_stmts[0]
        pos = self.get_metadata(PositionProvider, orig_first)
        self.violations.append(
            Violation(
                file=self._filename,
                line=pos.start.line,
                column=pos.start.column,
                rule="DOCSTRING_REMOVED",
                message=f"{context} docstring removed",
            )
        )
        remaining = stmts[1:]
        if remaining:
            first_remaining = remaining[0]
            if self._config.remove_blank_lines and isinstance(
                first_remaining, (cst.SimpleStatementLine, cst.BaseCompoundStatement)
            ):
                # Drop the blank lines that separated the docstring from the
                # body, but not a comment that survived (``# pystrip: keep``).
                kept = [line for line in first_remaining.leading_lines if line.comment is not None]
                remaining[0] = first_remaining.with_changes(leading_lines=kept)
            return body.with_changes(body=remaining)
        # Body would be empty - insert placeholder
        return body.with_changes(body=[self._make_placeholder_stmt()])

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_docstrings:
            new_body = self._remove_docstring_from_body(
                updated_node.body,
                original_node.body,
                "Function",
            )
            updated_node = updated_node.with_changes(body=new_body)

        if self._config.remove_type_annotations and updated_node.returns is not None:
            pos = self.get_metadata(PositionProvider, original_node)
            self.violations.append(
                Violation(
                    file=self._filename,
                    line=pos.start.line,
                    column=pos.start.column,
                    rule="TYPE_ANNOTATION_REMOVED",
                    message="Return type annotation removed",
                )
            )
            updated_node = updated_node.with_changes(returns=None)

        return updated_node

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_docstrings:
            new_body = self._remove_docstring_from_body(
                updated_node.body,
                original_node.body,
                "Class",
            )
            updated_node = updated_node.with_changes(body=new_body)

        return updated_node

    # ------------------------------------------------------------------
    # Type annotation removal
    # ------------------------------------------------------------------

    def leave_Param(
        self,
        original_node: cst.Param,
        updated_node: cst.Param,
    ) -> cst.Param | cst.MaybeSentinel | cst.RemovalSentinel:
        if self._config.remove_type_annotations and updated_node.annotation is not None:
            pos = self.get_metadata(PositionProvider, original_node)
            self.violations.append(
                Violation(
                    file=self._filename,
                    line=pos.start.line,
                    column=pos.start.column,
                    rule="TYPE_ANNOTATION_REMOVED",
                    message="Parameter type annotation removed",
                )
            )
            return updated_node.with_changes(annotation=None)
        return updated_node

    def leave_AnnAssign(
        self,
        original_node: cst.AnnAssign,
        updated_node: cst.AnnAssign,
    ) -> cst.BaseSmallStatement:
        if not self._config.remove_type_annotations or self._keep_depth:
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        self.violations.append(
            Violation(
                file=self._filename,
                line=pos.start.line,
                column=pos.start.column,
                rule="TYPE_ANNOTATION_REMOVED",
                message="Type annotation removed",
            )
        )

        if updated_node.value is not None:
            # x: T = v  ->  x = v
            equal = updated_node.equal
            if isinstance(equal, cst.AssignEqual):
                ws_before = (
                    equal.whitespace_before
                    if isinstance(equal.whitespace_before, cst.SimpleWhitespace)
                    else cst.SimpleWhitespace(" ")
                )
                ws_after = (
                    equal.whitespace_after
                    if isinstance(equal.whitespace_after, cst.SimpleWhitespace)
                    else cst.SimpleWhitespace(" ")
                )
                assign_target = cst.AssignTarget(
                    target=updated_node.target,
                    whitespace_before_equal=ws_before,
                    whitespace_after_equal=ws_after,
                )
            else:
                assign_target = cst.AssignTarget(target=updated_node.target)
            return cst.Assign(
                targets=[assign_target],
                value=updated_node.value,
            )

        # x: T  (no value) – return unchanged; the enclosing block handler will drop
        # the entire SimpleStatementLine.
        return updated_node

    def leave_IndentedBlock(
        self,
        original_node: cst.IndentedBlock,  # noqa: ARG002 - libcst signature
        updated_node: cst.IndentedBlock,
    ) -> cst.BaseSuite:
        if not self._config.remove_type_annotations:
            return updated_node
        new_body = _filter_annotation_only_lines(updated_node.body)
        if len(new_body) == len(updated_node.body):
            return updated_node
        if new_body:
            return updated_node.with_changes(body=new_body)
        # All statements were annotation-only – insert a placeholder to keep the block valid.
        return updated_node.with_changes(body=[self._make_placeholder_stmt()])
