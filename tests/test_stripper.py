"""Tests for the core stripping logic."""

from __future__ import annotations

from pystrip.stripper import StripConfig, strip_code


def make_config(**kwargs: object) -> StripConfig:
    return StripConfig(**kwargs)  # type: ignore[arg-type]


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

    def test_empty_function_body_gets_pass(self) -> None:
        source = 'def foo():\n    """Only docstring."""\n'
        result = strip_code(source, make_config(remove_comments=False, remove_docstrings=True))
        assert "pass" in result.modified_code

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
