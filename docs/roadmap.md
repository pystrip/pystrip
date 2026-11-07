# Roadmap

Candidate features and integrations, ranked by value against effort. Nothing
here is committed; it is a menu for deciding what to build next. Each item notes
the practical value, the rough effort, and the main risk.

## High value, low-to-medium effort

### 1. Inline keep/skip pragmas

Let a source file opt out of stripping with directives such as
`# pystrip: keep` on the comment or docstring to preserve, and
`# pystrip: skip-file` at the top of a file. This removes the biggest limitation
of an all-or-nothing stripper: today you must exclude a whole file to protect a
single license banner or explanatory comment.

- **Value:** high — the most common real-world objection.
- **Effort:** medium — the visitor already inspects comment nodes.
- **Risk:** low — opt-in; no change to existing behaviour.

### 2. Keep file-header / license comments

A `--keep-header` flag (and config key) that preserves the leading comment block
of a file, so copyright and SPDX license headers survive a strip.

- **Value:** high — losing license headers is a frequent, serious surprise.
- **Effort:** low-medium.
- **Risk:** low — opt-in.

### 3. Respect `.gitignore`

When collecting files, skip anything git ignores, matching the default users
expect from modern tools.

- **Value:** medium-high.
- **Effort:** low-medium — shell out to `git ls-files`, or use `pathspec`.
- **Risk:** low — can be gated behind a flag to stay deterministic.

### 4. `--stdin-filename`

Let stdin mode carry a filename so per-path config applies and violations report
a real path. This is what editors need to call pystrip as a formatter, the way
ruff and black are wired in.

- **Value:** medium-high — unlocks editor integration.
- **Effort:** low.
- **Risk:** low.

### 5. Publish the GitHub Action to the Marketplace

The composite `action.yml` already exists. Publishing it under a `v1` tag on the
GitHub Marketplace makes `uses: pystrip/pystrip@v1` discoverable.

- **Value:** medium — distribution and visibility.
- **Effort:** low — a release step, no code.
- **Risk:** low.

## Medium value, medium effort

### 6. `.pyi` stub awareness

Treat `.pyi` stub files correctly: never strip annotations from them, since
annotations are their entire purpose.

- **Value:** medium for typed libraries.
- **Effort:** low-medium.
- **Risk:** low.

### 7. Jupyter notebook support

Strip comments and docstrings inside `.ipynb` code cells.

- **Value:** medium — notebooks are a common Python surface.
- **Effort:** medium — parse `nbformat`, process each code cell.
- **Risk:** medium — round-tripping notebook JSON cleanly.

### 8. Per-rule selection

A ruff-style `select` / `ignore` model over the rule set
(`COMMENT_REMOVED`, `DOCSTRING_REMOVED`, `TYPE_ANNOTATION_REMOVED`), replacing
the current `--keep-*` flags with a single consistent mechanism.

- **Value:** medium — nicer ergonomics, familiar to ruff users.
- **Effort:** medium — config and CLI redesign with back-compat.
- **Risk:** medium — must not break existing `--keep-*` users.

## Lower priority / larger bets

### 9. Browser playground

A "try pystrip" page on the docs site, running the stripper client-side via
Pyodide/WebAssembly.

- **Value:** medium — great for onboarding and demos.
- **Effort:** high.
- **Risk:** medium — libcst under Pyodide.

## Known issues to triage (not features)

- **PEP 263 encoding cookie.** Removing `# -*- coding: latin-1 -*-` from a
  non-UTF-8 file changes how CPython decodes it. This is pre-existing upstream
  behaviour, documented in the [FAQ](faq.md); a guard or warning could be added.
- **Dry-run summary label.** A dry run can print `Changed N file(s)` where
  `Would change` is clearer. Cosmetic, pre-existing.
