"""libcst-based transformer for removing comments and docstrings."""

from __future__ import annotations

from collections.abc import Sequence

import libcst as cst
from libcst import CSTTransformer
from libcst.metadata import PositionProvider

from pystrip.stripper import StripConfig, Violation


def _is_docstring_node(node: cst.BaseStatement) -> bool:
    """Return True if node is a docstring (expression statement with a string literal)."""
    if not isinstance(node, cst.SimpleStatementLine):
        return False
    if len(node.body) != 1:
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

    def __init__(self, config: StripConfig, filename: str = "<unknown>") -> None:
        super().__init__()
        self._config = config
        self._filename = filename
        self.violations: list[Violation] = []
        self._body_depth: int = 0  # track nesting for docstring detection

    # ------------------------------------------------------------------
    # Comment removal
    # ------------------------------------------------------------------

    def _strip_comment_from_line(
        self, original_line: cst.EmptyLine, updated_line: cst.EmptyLine
    ) -> cst.EmptyLine | None:
        """Remove comment from a leading empty line.

        Returns None if the line was comment-only and blank-line removal is on
        (meaning the line itself should be dropped entirely).
        """
        if original_line.comment is not None:
            pos = self.get_metadata(PositionProvider, original_line)
            self.violations.append(
                Violation(
                    file=self._filename,
                    line=pos.start.line,
                    column=pos.start.column,
                    rule="COMMENT_REMOVED",
                    message="Leading comment removed",
                )
            )
            if self._config.remove_blank_lines:
                return None
            return updated_line.with_changes(comment=None)
        return updated_line

    def _strip_trailing_comment(
        self,
        original_trailing_whitespace: cst.TrailingWhitespace,
        updated_trailing_whitespace: cst.TrailingWhitespace,
    ) -> cst.TrailingWhitespace:
        if original_trailing_whitespace.comment is not None:
            pos = self.get_metadata(PositionProvider, original_trailing_whitespace)
            self.violations.append(
                Violation(
                    file=self._filename,
                    line=pos.start.line,
                    column=pos.start.column,
                    rule="COMMENT_REMOVED",
                    message="Trailing comment removed",
                )
            )
            return updated_trailing_whitespace.with_changes(
                comment=None,
                whitespace=cst.SimpleWhitespace(""),
            )
        return updated_trailing_whitespace

    # ------------------------------------------------------------------
    # Module-level
    # ------------------------------------------------------------------

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                header=self._filter_leading_lines(original_node.header, updated_node.header)
            )

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
                    updated_node = updated_node.with_changes(
                        body=[
                            cst.SimpleStatementLine(
                                body=[cst.Pass()],
                            )
                        ]
                    )

        if self._config.remove_type_annotations:
            new_body = _filter_annotation_only_lines(updated_node.body)
            if len(new_body) < len(updated_node.body):
                if new_body:
                    updated_node = updated_node.with_changes(body=new_body)
                else:
                    updated_node = updated_node.with_changes(
                        body=[cst.SimpleStatementLine(body=[cst.Pass()])]
                    )

        return updated_node

    # ------------------------------------------------------------------
    # Statement-level comment removal
    # ------------------------------------------------------------------

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
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

        if self._config.remove_comments:
            # Strip leading comments (drop the line entirely if it was comment-only)
            new_trailing = self._strip_trailing_comment(
                original_node.trailing_whitespace,
                updated_node.trailing_whitespace,
            )
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                ),
                trailing_whitespace=new_trailing,
            )
        return updated_node

    def leave_BaseCompoundStatement(
        self,
        original_node: cst.BaseCompoundStatement,
        updated_node: cst.BaseCompoundStatement,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        # For compound statements, remove leading_lines comments
        if self._config.remove_comments and hasattr(updated_node, "leading_lines"):
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
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
            if self._config.remove_blank_lines and hasattr(remaining[0], "leading_lines"):
                remaining[0] = remaining[0].with_changes(leading_lines=[])
            return body.with_changes(body=remaining)
        # Body would be empty - insert pass
        return body.with_changes(
            body=[
                cst.SimpleStatementLine(
                    body=[cst.Pass()],
                )
            ]
        )

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments and hasattr(updated_node, "leading_lines"):
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )

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
        if self._config.remove_comments and hasattr(updated_node, "leading_lines"):
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )

        if self._config.remove_docstrings:
            new_body = self._remove_docstring_from_body(
                updated_node.body,
                original_node.body,
                "Class",
            )
            updated_node = updated_node.with_changes(body=new_body)

        return updated_node

    def _filter_leading_lines(
        self,
        original_lines: Sequence[cst.EmptyLine],
        updated_lines: Sequence[cst.EmptyLine],
    ) -> list[cst.EmptyLine]:
        """Strip comments from leading lines, dropping comment-only lines if configured."""
        result: list[cst.EmptyLine] = []
        for original_line, updated_line in zip(original_lines, updated_lines, strict=False):
            stripped = self._strip_comment_from_line(original_line, updated_line)
            if stripped is not None:
                result.append(stripped)
        return result

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
        if not self._config.remove_type_annotations:
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
        original_node: cst.IndentedBlock,  # noqa: ARG002
        updated_node: cst.IndentedBlock,
    ) -> cst.BaseSuite:
        if not self._config.remove_type_annotations:
            return updated_node
        new_body = _filter_annotation_only_lines(updated_node.body)
        if len(new_body) == len(updated_node.body):
            return updated_node
        if new_body:
            return updated_node.with_changes(body=new_body)
        # All statements were annotation-only – insert a pass to keep the block valid.
        return updated_node.with_changes(body=[cst.SimpleStatementLine(body=[cst.Pass()])])

    # ------------------------------------------------------------------
    # Inline comment removal on if/for/while/with/try
    # ------------------------------------------------------------------

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
        return updated_node

    def leave_For(
        self, original_node: cst.For, updated_node: cst.For
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
        return updated_node

    def leave_While(
        self, original_node: cst.While, updated_node: cst.While
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
        return updated_node

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
        return updated_node

    def leave_Try(
        self, original_node: cst.Try, updated_node: cst.Try
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=self._filter_leading_lines(
                    original_node.leading_lines,
                    updated_node.leading_lines,
                )
            )
        return updated_node
