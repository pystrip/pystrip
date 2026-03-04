"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def simple_module_with_docstring() -> str:
    return '"""Module docstring."""\n\nx = 1\n'


@pytest.fixture
def simple_module_with_comment() -> str:
    return "# This is a comment\nx = 1\n"


@pytest.fixture
def function_with_docstring() -> str:
    return 'def foo():\n    """Function docstring."""\n    return 1\n'


@pytest.fixture
def class_with_docstring() -> str:
    return 'class Foo:\n    """Class docstring."""\n    pass\n'
