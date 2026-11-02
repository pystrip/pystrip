"""Tests for the core stripping logic."""

from __future__ import annotations

import io
import tokenize

from pystrip.stripper import StripConfig, strip_code


def make_config(**kwargs: object) -> StripConfig:
    return StripConfig(**kwargs)  # type: ignore[arg-type]


def comment_tokens(code: str) -> list[str]:
    """Return every comment in code.

    Tokenizing rather than searching for ``#`` matters: a ``#`` inside a string
    literal is not a comment, and a comment does not have to contain anything
    that a substring search would recognise.
    """
    tokens = tokenize.generate_tokens(io.StringIO(code).readline)
    return [tok.string for tok in tokens if tok.type == tokenize.COMMENT]


def assert_stripped(source: str) -> str:
    """Strip comments from source and assert nothing recognisable survives.

    Both halves are required: a stripper that drops comments by mangling the
    code is not a stripper, so the output has to still compile.
    """
    result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
    assert comment_tokens(result.modified_code) == []
    compile(result.modified_code, "<stripped>", "exec")
    assert result.changed is True
    return result.modified_code


class TestCommentRemoval:
    def test_removes_inline_comment(self) -> None:
        source = "x = 1  # inline comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# inline comment" not in result.modified_code
        assert "x = 1" in result.modified_code
        assert result.changed is True

    def test_removes_standalone_comment(self) -> None:
        source = "# standalone comment\nx = 1\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# standalone comment" not in result.modified_code
        assert result.changed is True

    def test_keeps_string_with_hash(self) -> None:
        source = 'x = "hello # not a comment"\n'
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert '"hello # not a comment"' in result.modified_code

    def test_no_comment_no_change(self) -> None:
        source = "x = 1\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert result.changed is False

    def test_comment_violations_recorded_with_lines(self) -> None:
        source = "# first\nx = 1  # second\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="sample.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 2
        assert all(v.file == "sample.py" for v in comment_violations)
        assert {v.line for v in comment_violations} == {1, 2}


class TestDocstringRemoval:
    def test_removes_module_docstring(self) -> None:
        source = '"""Module docstring."""\n\nx = 1\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert '"""Module docstring."""' not in result.modified_code
        assert "x = 1" in result.modified_code
        assert result.changed is True

    def test_removes_function_docstring(self) -> None:
        source = 'def foo():\n    """Function docstring."""\n    return 1\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert '"""Function docstring."""' not in result.modified_code
        assert "return 1" in result.modified_code

    def test_removes_class_docstring(self) -> None:
        source = 'class Foo:\n    """Class docstring."""\n    pass\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert '"""Class docstring."""' not in result.modified_code

    def test_does_not_remove_regular_string(self) -> None:
        source = 'x = 1\nsentinel = "keep me"\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert '"keep me"' in result.modified_code
        assert result.changed is False

    def test_empty_function_body_gets_ellipsis(self) -> None:
        source = 'def foo():\n    """Only docstring."""\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert "..." in result.modified_code

    def test_violations_recorded(self) -> None:
        source = '"""Module docstring."""\n\nx = 1\n'
        result = strip_code(
            source,
            make_config(remove_comments=False, remove_docstrings=True, filename="test.py"),
        )
        assert len(result.violations) == 1
        assert result.violations[0].rule == "DOCSTRING_REMOVED"
        assert result.violations[0].file == "test.py"
        assert result.violations[0].line == 1

    def test_keeps_non_first_string(self) -> None:
        source = 'x = 1\n"not a docstring"\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert '"not a docstring"' in result.modified_code


class TestTypeAnnotationRemoval:
    def _cfg(self, **kwargs: object) -> StripConfig:
        defaults = dict(
            remove_comments=False, remove_docstrings=False, remove_type_annotations=True
        )
        defaults.update(kwargs)
        return make_config(**defaults)

    def test_removes_param_annotation(self) -> None:
        source = "def foo(x: int) -> None:\n    pass\n"
        result = strip_code(source, self._cfg())
        assert ": int" not in result.modified_code
        assert "-> None" not in result.modified_code
        assert "def foo(x)" in result.modified_code
        assert result.changed is True

    def test_removes_return_annotation(self) -> None:
        source = "def foo() -> int:\n    return 1\n"
        result = strip_code(source, self._cfg())
        assert "-> int" not in result.modified_code
        assert "def foo():" in result.modified_code

    def test_removes_annotated_assignment_with_value(self) -> None:
        source = "x: int = 5\n"
        result = strip_code(source, self._cfg())
        assert ": int" not in result.modified_code
        assert "x = 5" in result.modified_code
        assert result.changed is True

    def test_removes_annotation_only_statement(self) -> None:
        source = "x: int\n"
        result = strip_code(source, self._cfg())
        assert "x: int" not in result.modified_code
        assert result.changed is True

    def test_annotation_only_in_function_body_inserts_ellipsis(self) -> None:
        source = "def foo():\n    x: int\n"
        result = strip_code(source, self._cfg())
        assert "x: int" not in result.modified_code
        assert "..." in result.modified_code

    def test_annotation_only_in_class_body_inserts_ellipsis(self) -> None:
        source = "class Foo:\n    name: str\n"
        result = strip_code(source, self._cfg())
        assert "name: str" not in result.modified_code
        assert "..." in result.modified_code

    def test_class_annotated_assignment_with_value(self) -> None:
        source = "class Foo:\n    count: int = 0\n"
        result = strip_code(source, self._cfg())
        assert ": int" not in result.modified_code
        assert "count = 0" in result.modified_code

    def test_keeps_annotations_when_disabled(self) -> None:
        source = "def foo(x: int) -> str:\n    y: bool = True\n    return str(x)\n"
        result = strip_code(
            source,
            make_config(
                remove_comments=False,
                remove_docstrings=False,
                remove_type_annotations=False,
            ),
        )
        assert result.changed is False
        assert ": int" in result.modified_code
        assert "-> str" in result.modified_code

    def test_violations_recorded(self) -> None:
        source = "def foo(x: int) -> str:\n    y: bool = True\n    return str(x)\n"
        result = strip_code(
            source,
            make_config(
                remove_comments=False,
                remove_docstrings=False,
                remove_type_annotations=True,
                filename="ann.py",
            ),
        )
        annotation_violations = [
            v for v in result.violations if v.rule == "TYPE_ANNOTATION_REMOVED"
        ]
        # x: int (param), -> str (return), y: bool = True (var)
        assert len(annotation_violations) == 3
        assert all(v.file == "ann.py" for v in annotation_violations)

    def test_removes_multiple_params_annotations(self) -> None:
        source = "def foo(a: int, b: str, c: float = 1.0) -> None:\n    pass\n"
        result = strip_code(source, self._cfg())
        assert ": int" not in result.modified_code
        assert ": str" not in result.modified_code
        assert ": float" not in result.modified_code
        assert "-> None" not in result.modified_code
        assert (
            "def foo(a, b, c = 1.0)" in result.modified_code
            or "def foo(a, b, c=1.0)" in result.modified_code
        )

    def test_module_annotation_only_removed(self) -> None:
        source = "x: int\ny = 1\n"
        result = strip_code(source, self._cfg())
        assert "x: int" not in result.modified_code
        assert "y = 1" in result.modified_code


class TestShebangHandling:
    def test_shebang_preserved_by_default(self) -> None:
        source = "#!/usr/bin/env python3\nx = 1\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "#!/usr/bin/env python3" in result.modified_code
        assert result.changed is False

    def test_shebang_removed_with_flag(self) -> None:
        source = "#!/usr/bin/env python3\nx = 1\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_shebang=True),
        )
        assert "#!/usr/bin/env python3" not in result.modified_code
        assert result.changed is True

    def test_regular_comment_still_removed_with_shebang(self) -> None:
        source = "#!/usr/bin/env python3\n# normal comment\nx = 1\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "#!/usr/bin/env python3" in result.modified_code
        assert "# normal comment" not in result.modified_code


class TestIndentedBlockFooterComments:
    def test_removes_comment_after_last_statement_in_function(self) -> None:
        source = "def meth(self):\n    pass\n    # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert result.changed is True

    def test_removes_comment_after_last_statement_in_class_method(self) -> None:
        source = "class Foo:\n    def meth(self):\n        pass\n        # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert result.changed is True

    def test_footer_comment_violation_recorded(self) -> None:
        source = "def foo():\n    x = 1\n    # trailing\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="f.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 3


class TestInlineCommentOnCompoundStatement:
    """Regression tests for inline comments on compound statement header lines."""

    def test_removes_inline_comment_on_if(self) -> None:
        source = "if x:  # if comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# if comment" not in result.modified_code
        assert "if x:" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_for(self) -> None:
        source = "for i in lst:  # for comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# for comment" not in result.modified_code
        assert "for i in lst:" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_while(self) -> None:
        source = "while cond:  # while comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# while comment" not in result.modified_code
        assert "while cond:" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_with(self) -> None:
        source = "with open('f') as fh:  # with comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# with comment" not in result.modified_code
        assert "with open('f') as fh:" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_try(self) -> None:
        source = "try:  # try comment\n    pass\nexcept Exception:\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# try comment" not in result.modified_code
        assert "try:" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_def(self) -> None:
        source = "def foo():  # def comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# def comment" not in result.modified_code
        assert "def foo():" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_class(self) -> None:
        source = "class Foo:  # class comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# class comment" not in result.modified_code
        assert "class Foo:" in result.modified_code
        assert result.changed is True

    def test_violation_recorded_for_compound_inline_comment(self) -> None:
        source = "if x:  # check\n    pass\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="t.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 1
        assert comment_violations[0].file == "t.py"

    def test_no_change_when_remove_comments_disabled(self) -> None:
        source = "if x:  # comment\n    pass\n"
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=False))
        assert "# comment" in result.modified_code
        assert result.changed is False


class TestDecoratorComments:
    """Regression tests for comments on decorator lines."""

    def test_removes_inline_comment_on_decorator(self) -> None:
        source = "@decorator  # decorator comment\ndef foo():\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# decorator comment" not in result.modified_code
        assert "@decorator" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_on_decorator_with_args(self) -> None:
        source = "@decorator(arg)  # decorator comment\ndef foo():\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# decorator comment" not in result.modified_code
        assert "@decorator(arg)" in result.modified_code
        assert result.changed is True

    def test_removes_comment_between_decorators(self) -> None:
        source = "@dec1\n# between decorators\n@dec2\ndef foo():\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# between decorators" not in result.modified_code
        assert "@dec1" in result.modified_code
        assert "@dec2" in result.modified_code
        assert result.changed is True

    def test_decorator_comment_violation_recorded(self) -> None:
        source = "@decorator  # inline\ndef foo():\n    pass\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="d.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 1
        assert comment_violations[0].file == "d.py"

    def test_no_change_when_remove_comments_disabled_on_decorator(self) -> None:
        source = "@decorator  # comment\ndef foo():\n    pass\n"
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=False))
        assert "# comment" in result.modified_code
        assert result.changed is False


class TestParenthesizedExpressionComments:
    """Regression tests for comments inside parenthesized expressions."""

    def test_removes_inline_comment_in_multiline_def_params(self) -> None:
        source = "def foo(\n    a,  # param comment\n    b,\n):\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# param comment" not in result.modified_code
        assert "def foo(" in result.modified_code
        assert result.changed is True

    def test_removes_standalone_comment_inside_call(self) -> None:
        source = "foo(\n    # standalone comment\n    a,\n)\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# standalone comment" not in result.modified_code
        assert "foo(" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_in_multiline_if_condition(self) -> None:
        source = "if (x and  # condition comment\n    y):\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# condition comment" not in result.modified_code
        assert "if (x and" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_in_class_bases(self) -> None:
        source = "class Foo(\n    Base,  # base comment\n):\n    pass\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# base comment" not in result.modified_code
        assert "class Foo(" in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_in_parenthesized_with(self) -> None:
        source = 'with (\n    open("a") as f,  # with comment\n    open("b") as g,\n):\n    pass\n'
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# with comment" not in result.modified_code
        assert result.changed is True

    def test_removes_inline_comment_in_multiline_return(self) -> None:
        source = "def foo():\n    return (\n        1 +  # add comment\n        2\n    )\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# add comment" not in result.modified_code
        assert result.changed is True

    def test_parenthesized_comment_violation_recorded(self) -> None:
        source = "def foo(\n    a,  # param\n    b,\n):\n    pass\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="p.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 2
        assert comment_violations[0].file == "p.py"

    def test_no_change_when_remove_comments_disabled_in_parens(self) -> None:
        source = "def foo(\n    a,  # comment\n    b,\n):\n    pass\n"
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=False))
        assert "# comment" in result.modified_code
        assert result.changed is False


class TestOneLiners:
    """Regression tests for inline comments on one-liner compound statements."""

    def test_removes_comment_on_one_liner_def(self) -> None:
        source = "def foo(): pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "def foo(): pass" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_def_with_return(self) -> None:
        source = "def foo(): return 1  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "return 1" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_class(self) -> None:
        source = "class Foo: pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "class Foo: pass" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_if(self) -> None:
        source = "if x: pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "if x: pass" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_for(self) -> None:
        source = "for i in lst: pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "for i in lst: pass" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_while(self) -> None:
        source = "while cond: break  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "while cond: break" in result.modified_code
        assert result.changed is True

    def test_removes_comment_on_one_liner_with(self) -> None:
        source = "with ctx(): pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert "# comment" not in result.modified_code
        assert "with ctx(): pass" in result.modified_code
        assert result.changed is True

    def test_one_liner_comment_violation_recorded(self) -> None:
        source = "def foo(): pass  # comment\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="ol.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 1
        assert comment_violations[0].file == "ol.py"

    def test_no_change_when_remove_comments_disabled_on_one_liner(self) -> None:
        source = "def foo(): pass  # comment\n"
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=False))
        assert "# comment" in result.modified_code
        assert result.changed is False


class TestPlaceholderStyle:
    def test_default_uses_ellipsis_for_empty_docstring_body(self) -> None:
        source = 'def foo():\n    """Docstring."""\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert "..." in result.modified_code
        assert "pass" not in result.modified_code

    def test_use_pass_flag_inserts_pass(self) -> None:
        source = 'def foo():\n    """Docstring."""\n'
        result = strip_code(
            source,
            make_config(remove_comments=False, remove_docstrings=True, use_pass=True),
        )
        assert "pass" in result.modified_code
        assert "..." not in result.modified_code

    def test_use_pass_for_annotation_only_body(self) -> None:
        source = "def foo():\n    x: int\n"
        result = strip_code(
            source,
            make_config(
                remove_comments=False,
                remove_docstrings=False,
                remove_type_annotations=True,
                use_pass=True,
            ),
        )
        assert "pass" in result.modified_code
        assert "..." not in result.modified_code


class TestCommentPositionCoverage:
    """One test per CST position where a comment used to survive a strip.

    Each name carries the libcst field the comment lands in, because that field
    — not the surface syntax — is what the stripper has to handle. Enumerating
    statement types leaks every type the author did not list; handling the two
    fields that can hold a comment cannot.
    """

    def test_module_footer(self) -> None:
        # Any comment after the last top-level statement. The most common real
        # placement, and the one a comment-only file does not exercise: with no
        # body, libcst files the comment under Module.header instead.
        assert_stripped("x = 1\n# footer note\n")

    def test_else_leading_lines_of_if(self) -> None:
        assert_stripped("if x:\n    a = 1\n# why else\nelse:\n    b = 2\n")

    def test_else_leading_lines_of_for(self) -> None:
        assert_stripped("for i in x:\n    a = 1\n# why else\nelse:\n    b = 2\n")

    def test_else_leading_lines_of_while(self) -> None:
        assert_stripped("while x:\n    a = 1\n# why else\nelse:\n    b = 2\n")

    def test_else_leading_lines_of_try(self) -> None:
        assert_stripped(
            "try:\n    a = 1\nexcept ValueError:\n    b = 2\n# why else\nelse:\n    c = 3\n"
        )

    def test_except_handler_leading_lines(self) -> None:
        # The canonical place to explain a swallowed exception.
        assert_stripped("try:\n    a = 1\n# swallowed on purpose\nexcept ValueError:\n    b = 2\n")

    def test_finally_leading_lines(self) -> None:
        assert_stripped(
            "try:\n    a = 1\nexcept ValueError:\n    b = 2\n# cleanup\nfinally:\n    c = 3\n"
        )

    def test_except_star_handler_leading_lines(self) -> None:
        assert_stripped("try:\n    a = 1\n# group note\nexcept* ValueError:\n    b = 2\n")

    def test_try_star_leading_lines(self) -> None:
        # TryStar is a distinct class from Try, so a leave_Try handler misses it.
        assert_stripped("z = 0\n# note\ntry:\n    a = 1\nexcept* ValueError:\n    b = 2\n")

    def test_match_leading_lines(self) -> None:
        assert_stripped("z = 0\n# note\nmatch x:\n    case 1:\n        a = 1\n")

    def test_match_case_leading_lines(self) -> None:
        assert_stripped(
            "match x:\n    case 1:\n        a = 1\n    # arm note\n    case 2:\n        b = 2\n"
        )

    def test_function_def_lines_after_decorators(self) -> None:
        assert_stripped("@d\n# note\ndef f():\n    pass\n")

    def test_class_def_lines_after_decorators(self) -> None:
        assert_stripped("@d\n# note\nclass K:\n    a = 1\n")

    def test_bang_comment_away_from_line_one_is_not_a_shebang(self) -> None:
        # A shebang is a property of physical line 1, not of the "#!" prefix.
        # Applying the rule position-blind makes "#!" a one-character opt-out of
        # the whole tool, and it is asymmetric: the same text as a trailing
        # comment (x = 1  #! bang) was always removed.
        assert_stripped("x = 1\n#! not a shebang here\ny = 2\n")

    def test_shebang_on_line_one_is_still_kept(self) -> None:
        source = "#!/usr/bin/env python3\nx = 1\n#! not a shebang here\n"
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert comment_tokens(result.modified_code) == ["#!/usr/bin/env python3"]
        assert result.modified_code.startswith("#!/usr/bin/env python3\n")

    def test_mixed_file_leaves_no_comment_anywhere(self) -> None:
        source = (
            "#!/usr/bin/env python3\n"
            "# head\n"
            "import os  # inline\n"
            "@d\n"
            "# after decorator\n"
            "def f(a):\n"
            "    # body\n"
            "    try:\n"
            "        return a  # deep inline\n"
            "    # before except\n"
            "    except ValueError:\n"
            "        pass\n"
            "    # before finally\n"
            "    finally:\n"
            "        pass\n"
            "    # block footer\n"
            "# module footer\n"
        )
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert comment_tokens(result.modified_code) == ["#!/usr/bin/env python3"]
        compile(result.modified_code, "<stripped>", "exec")

    def test_hash_inside_string_is_not_touched(self) -> None:
        source = 'x = "a # b"\n# real comment\ny = """\n# also a string\n"""\n'
        result = strip_code(source, make_config(remove_comments=True, remove_docstrings=False))
        assert comment_tokens(result.modified_code) == []
        assert '"a # b"' in result.modified_code
        assert "# also a string" in result.modified_code

    def test_no_change_when_remove_comments_disabled(self) -> None:
        source = "x = 1\n# footer note\n"
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=False))
        assert result.modified_code == source
        assert result.changed is False

    def test_newly_covered_positions_record_violations(self) -> None:
        # The violations list is what --check and every machine-readable format
        # report. A comment removed without a violation recorded is a silent
        # strip; a violation recorded without a removal is a false positive.
        source = "x = 1\n# footer note\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, filename="footer.py"),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].file == "footer.py"
        assert comment_violations[0].line == 2


class TestKeepBlankLines:
    """--keep-blank against the generic handlers.

    Dropping an EmptyLine drops the physical line, so every line below it moves
    up. That is correct by default, but --keep-blank exists so that stripping
    does not renumber the file: a traceback, a coverage report or a reviewer's
    line reference taken from the original still points at the same statement.
    So with blank-line removal off the line has to survive as a blank.
    """

    def test_keep_blank_preserves_line_numbers_of_following_code(self) -> None:
        source = "# header\nx = 1\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_blank_lines=False),
        )
        assert result.modified_code == "\nx = 1\n"
        assert result.modified_code.splitlines().index("x = 1") == source.splitlines().index(
            "x = 1"
        )

    def test_remove_blank_lines_drops_the_line_entirely(self) -> None:
        source = "# header\nx = 1\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_blank_lines=True),
        )
        assert result.modified_code == "x = 1\n"

    def test_keep_blank_in_module_footer(self) -> None:
        source = "x = 1\n# footer note\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_blank_lines=False),
        )
        assert comment_tokens(result.modified_code) == []
        assert result.modified_code == "x = 1\n\n"

    def test_keep_blank_before_else_keeps_the_line_and_compiles(self) -> None:
        source = "if x:\n    a = 1\n# why else\nelse:\n    b = 2\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_blank_lines=False),
        )
        assert comment_tokens(result.modified_code) == []
        assert result.modified_code == "if x:\n    a = 1\n\nelse:\n    b = 2\n"
        compile(result.modified_code, "<stripped>", "exec")

    def test_keep_blank_preserves_indented_block_footer_line(self) -> None:
        source = "def f():\n    a = 1\n    # block footer\nb = 2\n"
        result = strip_code(
            source,
            make_config(remove_comments=True, remove_docstrings=False, remove_blank_lines=False),
        )
        assert comment_tokens(result.modified_code) == []
        assert result.modified_code.splitlines().index("b = 2") == source.splitlines().index(
            "b = 2"
        )
        compile(result.modified_code, "<stripped>", "exec")

    def test_keep_blank_still_records_violations(self) -> None:
        source = "x = 1\n# footer note\n"
        result = strip_code(
            source,
            make_config(
                remove_comments=True,
                remove_docstrings=False,
                remove_blank_lines=False,
                filename="kb.py",
            ),
        )
        comment_violations = [v for v in result.violations if v.rule == "COMMENT_REMOVED"]
        assert len(comment_violations) == 1
        assert comment_violations[0].line == 2
