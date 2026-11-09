# Playground

Try pystrip on a snippet right in your browser. No install, no upload.

!!! info "Everything runs locally in your browser"
    This page loads a full Python runtime ([Pyodide](https://pyodide.org/), a
    WebAssembly build of CPython) and installs pystrip into it with
    [micropip](https://micropip.pyodide.org/). Your code never leaves the
    browser tab — nothing is uploaded to any server. The first load downloads
    roughly 15 MB and may take a few seconds; after that, the runtime stays
    cached for the rest of your visit.

<div id="pyodide-playground" markdown>

<p id="playground-status">Initializing…</p>

<div class="playground-options">
  <label><input type="checkbox" id="playground-keep-comments"> Keep comments</label>
  <label><input type="checkbox" id="playground-keep-docstrings"> Keep docstrings</label>
  <label><input type="checkbox" id="playground-keep-annotations"> Keep type annotations</label>
  <label><input type="checkbox" id="playground-keep-blank"> Keep blank lines</label>
  <label><input type="checkbox" id="playground-use-pass"> Use `pass` instead of `...`</label>
</div>

<div class="playground-controls">
  <button id="playground-run" type="button" disabled>Strip</button>
</div>

<div class="playground-grid">
  <div>
    <h3>Source</h3>
    <textarea id="playground-source" spellcheck="false">"""A tiny example module."""

from __future__ import annotations


def add(a: int, b: int) -> int:
    # Add two numbers together.
    return a + b  # inline comment
</textarea>
  </div>
  <div>
    <h3>Stripped output</h3>
    <pre id="playground-output"></pre>
  </div>
</div>

<h3>Violations</h3>
<ul id="playground-violations" class="playground-violations"></ul>

</div>

## How it works

The playground loads [Pyodide](https://pyodide.org/) and uses
[libcst](https://libcst.readthedocs.io/) (bundled with Pyodide) plus
[micropip](https://micropip.pyodide.org/) to install the real `pystrip`
package from PyPI, then calls the same public API you'd use locally:

```python
from pystrip.stripper import StripConfig, strip_code

result = strip_code(
    source,
    StripConfig(
        remove_comments=True,
        remove_docstrings=True,
        remove_type_annotations=True,
        remove_blank_lines=True,
        use_pass=False,
    ),
)

print(result.modified_code)
for violation in result.violations:
    print(violation.line, violation.column, violation.rule, violation.message)
```

The checkboxes above mirror the [CLI's `--keep-*` and `--use-pass`
flags](usage.md#what-gets-removed). If the source doesn't parse as valid
Python, the error pystrip raises is shown in place of the output.
