# Roadmap

Candidate features and integrations, ranked by value against effort. Nothing
here is committed; it is a menu for deciding what to build next. Each item notes
the practical value, the rough effort, and the main risk.

## Shipped in 1.5

The first nine items of this roadmap landed together in 1.5. Each links to the
documentation that now describes it.

| # | Feature | Where |
|---|---------|-------|
| 1 | Inline `# pystrip: keep` / `# pystrip: skip-file` pragmas | [Usage](usage.md#inline-pragmas) |
| 2 | `--keep-header` for shebang, encoding cookie, license banners | [Usage](usage.md#what-gets-removed) |
| 3 | `--respect-gitignore` | [Usage](usage.md#selecting-files) |
| 4 | `--stdin-filename` for editor integration | [Usage](usage.md#stdin-mode), [Integrations](integrations.md#editors) |
| 5 | GitHub Action on the Marketplace with a moving `v1` tag | [Integrations](integrations.md#marketplace-listing) |
| 6 | `.pyi` stub awareness | [Usage](usage.md#selecting-files) |
| 7 | Jupyter notebook support | [Usage](usage.md#selecting-files), [Python API](api.md#strip_notebook) |
| 8 | ruff-style `select` / `ignore` rule model | [Usage](usage.md#rule-selection), [Configuration](configuration.md) |
| 9 | Browser playground on Pyodide | [Playground](playground.md) |

## Candidates

### Per-directory configuration

Let a nested `pyproject.toml` or `.pystrip.toml` override the root settings for
its subtree, the way ruff resolves the closest configuration file.

- **Value:** medium — monorepos with mixed policies.
- **Effort:** medium — discovery per file, cache per directory.
- **Risk:** low — opt-in by presence of a nested file.

### Keep comments by pattern

A `keep_comment_patterns` list of regular expressions (for example `^# type:`,
`^# noqa`, `^# fmt:`) that protects tool directives without a pragma on every
line.

- **Value:** medium-high — `# type: ignore` and `# noqa` are load-bearing for
  other tools and today need `# pystrip: keep` each.
- **Effort:** low — one more check in the comment visitors.
- **Risk:** low.

### Encoding-cookie guard

Refuse to remove a PEP 263 cookie from a file that is not valid UTF-8, or warn,
instead of relying on the [FAQ](faq.md).

- **Value:** medium — turns a documented footgun into a loud failure.
- **Effort:** low.
- **Risk:** low.

### Language Server Protocol shim

A tiny LSP server exposing pystrip as a formatting provider, so editors need no
shell wiring at all.

- **Value:** medium.
- **Effort:** medium-high — a new process model and protocol surface.
- **Risk:** medium — maintenance of a second entry point.

## Known issues to triage (not features)

- **Dry-run summary label.** The GitHub and GitLab summary lines print
  `Changed N file(s)` even in `--check` mode, where the console summary already
  says `Would change`. Cosmetic, pre-existing.
