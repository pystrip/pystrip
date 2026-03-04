"""pystrip - Remove comments and docstrings from Python source files."""

from pystrip.stripper import StripConfig, StripResult, Violation, strip_code

__all__ = ["StripConfig", "StripResult", "Violation", "strip_code"]
__version__ = "0.1.0"
