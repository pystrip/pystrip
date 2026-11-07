# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `--version` flag.
- pre-commit hook definitions (`pystrip`, `pystrip-check`) and a reusable
  composite GitHub Action.
- MkDocs Material documentation site, deployed to GitHub Pages.
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, issue and pull-request templates, and Dependabot.

### Changed

- CI now runs on Python 3.11, 3.12, and 3.13, measures coverage with an 80%
  floor, and verifies the built package with `twine check`.

## [1.4.0] - 2026-11-06

### Fixed

- Comments are now removed by node type (`EmptyLine.comment`, `TrailingWhitespace.comment`) instead of per statement type, closing 14 input shapes over 7 CST positions where a comment survived a strip — including comments after the last top-level statement (`Module.footer`) and inside `except` handlers.
- A `#!` comment is only kept as a shebang on physical line 1; elsewhere it is now removed like any other comment.
- A parse error no longer prints `All files clean.` alongside it.

## [1.3.2] - 2026-04-30

### Fixed

- Inline comments on one-liner compound statements (`def foo(): pass  # comment`, `class Foo: pass  # comment`, `if x: pass  # comment`, etc.) are now correctly removed. Previously these were silently kept because the comment lives in `SimpleStatementSuite.trailing_whitespace` rather than any statement-level node that was already visited.

## [1.3.1] - 2026-04-30

### Fixed

- Inline comments on decorator lines (`@decorator  # comment`) are now correctly removed.
- Standalone comments between decorators are now correctly removed.
- Inline and standalone comments inside parenthesized expressions (multiline function parameters, function call arguments, `if`/`while` conditions, `with` items, class bases, and any other parenthesized expression) are now correctly removed.

## [1.3.0] - 2026-04-30

### Fixed

- Inline comments on compound statement header lines (`if`, `for`, `while`, `with`, `try`, `def`, `class`) are now correctly removed. Previously these comments were silently kept because they live in `IndentedBlock.header` rather than the statement's own leading lines.

## [1.2.0] - 2026-03-14

### Changed

- Validate configuration types and values strictly; invalid config now fails fast with clear errors instead of being silently ignored.

### Added

- Add `--continue-on-error` CLI mode to report per-file processing failures while continuing other files; runs still exit with code `2` when any processing error occurs.
- Add stdin/stdout mode via `pystrip -`, with stripped code written to stdout in normal mode and violation reporting preserved in `--check` mode.

## [1.1.0] - 2026-03-14

### Changed

- Fix trailing comment stripping
- Use `...` as empty-body placeholder, option `--use-pass` to use `pass` instead of `...`

### Added

- Preserve shebangs by default, option `--remove-shebang` to force shebang removal

## [1.0.0] - 2026-03-05

### Changed

- Switched to `hatch-vcs` for dynamic version management: the package version is now derived from git tags rather than being hardcoded in `pyproject.toml`.
- `__version__` in `src/pystrip/__init__.py` is now populated at runtime via `importlib.metadata`.
- SARIF driver output now reflects the installed package version dynamically.

## [0.1.0] - 2026-03-04

Initial public release of **pystrip**, a `libcst`-based Python comment/docstring stripper with both CLI and library APIs.

### Added

- Safe CST-based transformations using `libcst` (no regex/text-based stripping).
- CLI command `pystrip` with support for files/directories and recursive/non-recursive discovery.
- Library API exports:
  - `strip_code`
  - `StripConfig`
  - `StripResult`
  - `Violation`
- Comment stripping support:
  - Standalone comments
  - Inline comments
- Docstring stripping support for:
  - Module docstrings
  - Class docstrings
  - Function docstrings
- Preservation of regular string literals that are not docstrings.
- Automatic insertion of `pass` when docstring removal would leave an empty class/function/module body.
- Machine-readable output formats:
  - `text`
  - `json`
  - `sarif`
  - `gitlab`
  - `github`
- CI-oriented check mode (`--check`) with deterministic summaries.
- Diff preview mode (`--diff`).
- Write modes:
  - in-place (`--in-place`)
  - output directory (`--output-dir`)
- Config loading from:
  - `pyproject.toml` (`[tool.pystrip]`)
  - `.pystrip.toml` (`[pystrip]`)
  - explicit `--config` TOML path
- Config and CLI controls for excludes, glob excludes, docstring retention, blank-line retention, worker count, and output format.
- Parallel file processing via configurable worker jobs.
- Verbose diagnostics (`--verbose`) including per-comment locations and per-file removed comment counts.

### Behavior

- Exit codes:
  - `0`: clean/no changes needed
  - `1`: files would change in `--check` mode
  - `2`: runtime/CLI error
- Rule IDs emitted in reports:
  - `COMMENT_REMOVED`
  - `DOCSTRING_REMOVED`
- Summary fields included across structured outputs:
  - changed files
  - total violations
  - removed docstrings
  - removed comments
- Configuration precedence:
  - defaults < `pyproject.toml` < `.pystrip.toml` < explicit `--config` < CLI overrides

### Notes

- `--output-dir` currently writes changed files using each input file basename (no directory structure mirroring).
- Python requirement: `>=3.11`.
