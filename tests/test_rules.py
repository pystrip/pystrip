"""Tests for the ``select`` / ``ignore`` rule model and the new config keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from pystrip.config import ConfigError, PyStripConfig, load_config, parse_rule_list
from pystrip.stripper import RULES


def write_pyproject(tmp_path: Path, body: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(f"[tool.pystrip]\n{body}", encoding="utf-8")
    return tmp_path


class TestParseRuleList:
    def test_accepts_names_case_insensitively_and_comma_separated(self) -> None:
        assert parse_rule_list(["comment_removed,DOCSTRING_REMOVED", " all "], "x") == [
            "COMMENT_REMOVED",
            "DOCSTRING_REMOVED",
            "ALL",
        ]

    def test_rejects_unknown_rule_with_the_valid_names(self) -> None:
        with pytest.raises(ConfigError, match="Unknown rule 'NOPE' in --select") as exc:
            parse_rule_list(["NOPE"], "--select")
        for rule in RULES:
            assert rule in str(exc.value)


class TestResolveRules:
    def test_untouched_when_neither_set(self) -> None:
        cfg = PyStripConfig(remove_comments=False)
        cfg.resolve_rules()
        assert cfg.remove_comments is False
        assert cfg.remove_docstrings is True

    def test_select_enables_only_listed_rules(self) -> None:
        cfg = PyStripConfig(select=["DOCSTRING_REMOVED"])
        cfg.resolve_rules()
        assert (cfg.remove_comments, cfg.remove_docstrings, cfg.remove_type_annotations) == (
            False,
            True,
            False,
        )

    def test_ignore_subtracts_from_default_all(self) -> None:
        cfg = PyStripConfig(ignore=["TYPE_ANNOTATION_REMOVED"])
        cfg.resolve_rules()
        assert (cfg.remove_comments, cfg.remove_docstrings, cfg.remove_type_annotations) == (
            True,
            True,
            False,
        )

    def test_ignore_all_disables_everything(self) -> None:
        cfg = PyStripConfig(select=["ALL"], ignore=["ALL"])
        cfg.resolve_rules()
        assert not (cfg.remove_comments or cfg.remove_docstrings or cfg.remove_type_annotations)

    def test_select_overrides_remove_switches(self) -> None:
        # ``select`` is the source of truth once set, even against an explicit
        # ``remove_comments = false`` that came earlier in the config.
        cfg = PyStripConfig(remove_comments=False, select=["COMMENT_REMOVED"])
        cfg.resolve_rules()
        assert cfg.remove_comments is True


class TestConfigKeys:
    def test_loads_new_keys(self, tmp_path: Path) -> None:
        root = write_pyproject(
            tmp_path,
            'select = ["ALL"]\nignore = ["comment_removed"]\n'
            "keep_header = true\nrespect_gitignore = true\n",
        )
        cfg = load_config(root)
        assert cfg.select == ["ALL"]
        assert cfg.ignore == ["COMMENT_REMOVED"]
        assert cfg.keep_header is True
        assert cfg.respect_gitignore is True

    @pytest.mark.parametrize(
        "body, message",
        [
            ('select = "ALL"\n', "expected list"),
            ('select = ["BOGUS"]\n', "Unknown rule 'BOGUS'"),
            ("keep_header = 1\n", "expected bool"),
            ('respect_gitignore = "yes"\n', "expected bool"),
        ],
    )
    def test_rejects_invalid_values(self, tmp_path: Path, body: str, message: str) -> None:
        root = write_pyproject(tmp_path, body)
        with pytest.raises(ConfigError, match=message):
            load_config(root)
