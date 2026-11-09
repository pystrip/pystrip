"""Tests for inline pragmas, ``--keep-header``, and ``.pyi`` stub handling.

Each test encodes the reason the feature exists: a stripper that cannot be
told to leave one comment alone forces users to exclude whole files.
"""

from __future__ import annotations

from pystrip.stripper import StripConfig, header_end_line, strip_code


def rules(result: object) -> list[str]:
    return [v.rule for v in result.violations]  # type: ignore[attr-defined]


class TestKeepPragma:
    def test_comment_carrying_pragma_is_kept(self) -> None:
        source = "# license note  # pystrip: keep\n# gone\nx = 1\n"
        result = strip_code(source, StripConfig())
        assert "# license note  # pystrip: keep" in result.modified_code
        assert "# gone" not in result.modified_code
        assert rules(result) == ["COMMENT_REMOVED"]

    def test_trailing_pragma_comment_is_kept(self) -> None:
        source = "x = 1  # pystrip: keep\ny = 2  # bye\n"
        result = strip_code(source, StripConfig())
        assert "x = 1  # pystrip: keep" in result.modified_code
        assert "# bye" not in result.modified_code

    def test_pragma_protects_docstring_on_its_line(self) -> None:
        source = (
            '"""Module doc."""  # pystrip: keep\n\n'
            "def f():\n"
            '    """Kept."""  # pystrip: keep\n'
            "    return 1\n\n"
            "def g():\n"
            '    """Removed."""\n'
            "    return 2\n"
        )
        result = strip_code(source, StripConfig())
        assert '"""Module doc."""  # pystrip: keep' in result.modified_code
        assert '"""Kept."""  # pystrip: keep' in result.modified_code
        assert '"""Removed."""' not in result.modified_code
        assert rules(result) == ["DOCSTRING_REMOVED"]

    def test_pragma_protects_annotations_on_its_line(self) -> None:
        source = "x: int = 1  # pystrip: keep\ny: int  # pystrip: keep\nz: int = 2\nw: int\n"
        result = strip_code(source, StripConfig())
        assert "x: int = 1  # pystrip: keep" in result.modified_code
        assert "y: int  # pystrip: keep" in result.modified_code
        assert "z = 2" in result.modified_code
        assert "w" not in result.modified_code
        assert rules(result) == ["TYPE_ANNOTATION_REMOVED", "TYPE_ANNOTATION_REMOVED"]

    def test_kept_comment_survives_docstring_removal_in_body(self) -> None:
        # Removing a docstring also drops the blank lines after it; a kept
        # comment in that gap must not be collateral damage.
        source = 'def f():\n    """Doc."""\n\n    # why  # pystrip: keep\n    return 1\n'
        result = strip_code(source, StripConfig())
        assert "# why  # pystrip: keep" in result.modified_code
        assert '"""Doc."""' not in result.modified_code
        compile(result.modified_code, "<stripped>", "exec")

    def test_pragma_spelling_is_flexible(self) -> None:
        source = "#pystrip:keep\n# pystrip:   keep extra words\nx = 1\n"
        result = strip_code(source, StripConfig())
        assert result.changed is False

    def test_keeper_is_not_a_prefix_match(self) -> None:
        source = "# pystrip: keeper\nx = 1\n"
        result = strip_code(source, StripConfig())
        assert "# pystrip: keeper" not in result.modified_code


class TestSkipFilePragma:
    def test_skip_file_leaves_source_untouched(self) -> None:
        source = '"""Doc."""\n# pystrip: skip-file\n# comment\nx: int = 1\n'
        result = strip_code(source, StripConfig())
        assert result.modified_code == source
        assert result.changed is False
        assert result.skipped is True
        assert result.violations == []

    def test_skip_file_must_be_a_comment_line(self) -> None:
        source = 'x = "# pystrip: skip-file"  # gone\n'
        result = strip_code(source, StripConfig())
        assert result.skipped is False
        assert "# gone" not in result.modified_code

    def test_skip_file_in_string_literal_line_is_not_matched(self) -> None:
        source = 's = """\nnot # pystrip: skip-file\n"""\n# gone\n'
        result = strip_code(source, StripConfig())
        assert result.skipped is False


class TestKeepHeader:
    BANNER = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n# Copyright 2026\n# SPDX: MIT\n"

    def test_header_end_line_stops_at_first_blank(self) -> None:
        assert header_end_line(self.BANNER + "\n# attached\nx = 1\n") == 4

    def test_header_end_line_stops_at_first_code(self) -> None:
        assert header_end_line("# a\n# b\nx = 1  # c\n# d\n") == 2

    def test_header_end_line_zero_without_header(self) -> None:
        assert header_end_line("x = 1\n# a\n") == 0
        assert header_end_line("") == 0

    def test_keep_header_preserves_banner_only(self) -> None:
        source = self.BANNER + "\n# attached\nx = 1  # trailing\n"
        result = strip_code(source, StripConfig(keep_header=True))
        assert result.modified_code.startswith(self.BANNER)
        assert "# attached" not in result.modified_code
        assert "# trailing" not in result.modified_code
        assert rules(result) == ["COMMENT_REMOVED", "COMMENT_REMOVED"]

    def test_header_removed_by_default(self) -> None:
        source = self.BANNER + "\nx = 1\n"
        result = strip_code(source, StripConfig())
        assert "# Copyright 2026" not in result.modified_code
        # The shebang is still protected by its own rule.
        assert result.modified_code.startswith("#!/usr/bin/env python\n")

    def test_keep_header_with_remove_shebang_keeps_shebang_as_header(self) -> None:
        source = "#!/usr/bin/env python\n# banner\n\nx = 1\n"
        result = strip_code(source, StripConfig(keep_header=True, remove_shebang=True))
        assert result.modified_code.startswith("#!/usr/bin/env python\n# banner\n")

    def test_keep_header_does_not_protect_docstrings(self) -> None:
        source = '# banner\n"""Doc."""\nx = 1\n'
        result = strip_code(source, StripConfig(keep_header=True))
        assert "# banner" in result.modified_code
        assert '"""Doc."""' not in result.modified_code


class TestStubFiles:
    def test_pyi_keeps_annotations(self) -> None:
        source = "# comment\ndef f(x: int) -> int: ...\nclass A:\n    y: int\n"
        result = strip_code(source, StripConfig(filename="pkg/mod.pyi"))
        assert "def f(x: int) -> int: ..." in result.modified_code
        assert "    y: int" in result.modified_code
        assert "# comment" not in result.modified_code
        assert rules(result) == ["COMMENT_REMOVED"]

    def test_pyi_still_strips_docstrings(self) -> None:
        source = 'def f() -> int:\n    """Doc."""\n'
        result = strip_code(source, StripConfig(filename="mod.pyi"))
        assert result.modified_code == "def f() -> int:\n    ...\n"

    def test_py_file_still_strips_annotations(self) -> None:
        source = "def f(x: int) -> int: ...\n"
        result = strip_code(source, StripConfig(filename="mod.py"))
        assert result.modified_code == "def f(x): ...\n"
