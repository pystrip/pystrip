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
