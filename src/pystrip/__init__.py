"""pystrip - Remove comments and docstrings from Python source files."""

from importlib.metadata import PackageNotFoundError, version

from pystrip.stripper import StripConfig, StripResult, Violation, strip_code

__all__ = ["StripConfig", "StripResult", "Violation", "strip_code"]

try:
    __version__ = version("pystrip")
except PackageNotFoundError:
    # Package not installed (e.g., running directly from source without `pip install -e .`)
    __version__ = "0.0.0"
