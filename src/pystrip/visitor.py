"""libcst-based transformer for removing comments and docstrings."""

from __future__ import annotations

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

    def _strip_comment_from_line(self, line: cst.EmptyLine) -> cst.EmptyLine:
        """Remove comment from a leading empty line (keeping the line itself)."""
        if line.comment is not None:
            return line.with_changes(comment=None)
        return line

    def _strip_trailing_comment(
        self, trailing_whitespace: cst.TrailingWhitespace
    ) -> cst.TrailingWhitespace:
        if trailing_whitespace.comment is not None:
            return trailing_whitespace.with_changes(
                comment=None,
                whitespace=cst.SimpleWhitespace(""),
            )
        return trailing_whitespace

    # ------------------------------------------------------------------
    # Module-level
    # ------------------------------------------------------------------

    def visit_Module(self, node: cst.Module) -> bool:
        return True

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self._config.remove_comments:
            new_header: list[cst.EmptyLine] = []
            for line in updated_node.header:
                if line.comment is not None:
                    new_header.append(line.with_changes(comment=None))
                else:
                    new_header.append(line)
            updated_node = updated_node.with_changes(header=new_header)

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

        return updated_node

    # ------------------------------------------------------------------
    # Statement-level comment removal
    # ------------------------------------------------------------------

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            # Strip leading comments
            new_leading: list[cst.EmptyLine] = []
            for line in updated_node.leading_lines:
                new_leading.append(self._strip_comment_from_line(line))
            # Strip trailing comment
            new_trailing = self._strip_trailing_comment(updated_node.trailing_whitespace)
            updated_node = updated_node.with_changes(
                leading_lines=new_leading,
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
            new_leading: list[cst.EmptyLine] = []
            for line in updated_node.leading_lines:  # type: ignore[union-attr]
                new_leading.append(self._strip_comment_from_line(line))
            updated_node = updated_node.with_changes(leading_lines=new_leading)  # type: ignore[call-overload]
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
            list(original_body.body)
            if isinstance(original_body, cst.IndentedBlock)
            else stmts
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
            new_leading: list[cst.EmptyLine] = []
            for line in updated_node.leading_lines:
                new_leading.append(self._strip_comment_from_line(line))
            updated_node = updated_node.with_changes(leading_lines=new_leading)

        if self._config.remove_docstrings:
            new_body = self._remove_docstring_from_body(updated_node.body, original_node.body, "Function")
            updated_node = updated_node.with_changes(body=new_body)

        return updated_node

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments and hasattr(updated_node, "leading_lines"):
            new_leading: list[cst.EmptyLine] = []
            for line in updated_node.leading_lines:
                new_leading.append(self._strip_comment_from_line(line))
            updated_node = updated_node.with_changes(leading_lines=new_leading)

        if self._config.remove_docstrings:
            new_body = self._remove_docstring_from_body(updated_node.body, original_node.body, "Class")
            updated_node = updated_node.with_changes(body=new_body)

        return updated_node

    # ------------------------------------------------------------------
    # Inline comment removal on if/for/while/with/try
    # ------------------------------------------------------------------

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=[
                    self._strip_comment_from_line(l) for l in updated_node.leading_lines
                ]
            )
        return updated_node

    def leave_For(
        self, original_node: cst.For, updated_node: cst.For
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=[
                    self._strip_comment_from_line(l) for l in updated_node.leading_lines
                ]
            )
        return updated_node

    def leave_While(
        self, original_node: cst.While, updated_node: cst.While
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=[
                    self._strip_comment_from_line(l) for l in updated_node.leading_lines
                ]
            )
        return updated_node

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=[
                    self._strip_comment_from_line(l) for l in updated_node.leading_lines
                ]
            )
        return updated_node

    def leave_Try(
        self, original_node: cst.Try, updated_node: cst.Try
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if self._config.remove_comments:
            updated_node = updated_node.with_changes(
                leading_lines=[
                    self._strip_comment_from_line(l) for l in updated_node.leading_lines
                ]
            )
        return updated_node
