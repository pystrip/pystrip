/*
 * In-browser pystrip Playground, powered by Pyodide/WebAssembly.
 *
 * Pyodide is only downloaded when the playground elements are present on
 * the current page, and only once per visit: the heavy loadPyodide() /
 * micropip.install() work is memoised in `pyodideReadyPromise`, so revisiting
 * the page (including via Material's `navigation.instant` SPA-style
 * navigation) reuses the already-loaded runtime instead of fetching it again.
 *
 * Initialisation is driven by Material's `document$` observable, which fires
 * once per page view (both full loads and instant-navigation swaps). We
 * guard against wiring the same DOM node twice.
 */
(() => {
  "use strict";

  const PYODIDE_VERSION = "0.28.3";
  const PYODIDE_CDN_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

  // Memoised across page views so Pyodide/pystrip are downloaded at most once.
  let pyodideReadyPromise = null;

  // The DOM node we last wired up listeners for, to avoid double-binding
  // when document$ fires again for the same rendered container.
  let wiredContainer = null;

  function loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(script);
    });
  }

  function getPyodide(setStatus) {
    if (pyodideReadyPromise) {
      return pyodideReadyPromise;
    }

    pyodideReadyPromise = (async () => {
      setStatus("Loading Pyodide…");
      if (typeof loadPyodide === "undefined") {
        await loadScriptOnce(PYODIDE_CDN_BASE + "pyodide.js");
      }
      const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN_BASE });

      setStatus("Installing pystrip…");
      await pyodide.loadPackage(["micropip", "libcst"]);
      const micropip = pyodide.pyimport("micropip");
      await micropip.install("pystrip");

      return pyodide;
    })();

    // If loading fails, forget the cached promise so a retry (e.g. a fresh
    // page view) can try again instead of replaying the same error forever.
    pyodideReadyPromise.catch(() => {
      pyodideReadyPromise = null;
    });

    return pyodideReadyPromise;
  }

  const STRIP_SCRIPT = `
import json

from pystrip.stripper import StripConfig, strip_code

_config = StripConfig(
    remove_comments=not __keep_comments,
    remove_docstrings=not __keep_docstrings,
    remove_type_annotations=not __keep_annotations,
    remove_blank_lines=not __keep_blank,
    use_pass=bool(__use_pass),
    filename="<playground>",
)

try:
    _result = strip_code(__playground_source, _config)
    _payload = {
        "ok": True,
        "code": _result.modified_code,
        "violations": [
            {
                "line": v.line,
                "column": v.column,
                "rule": v.rule,
                "message": v.message,
            }
            for v in _result.violations
        ],
    }
except ValueError as exc:
    _payload = {"ok": False, "error": str(exc)}

json.dumps(_payload)
`;

  function escapeHtml(value) {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function initPlayground() {
    const container = document.getElementById("pyodide-playground");
    if (!container) {
      return;
    }
    if (wiredContainer === container) {
      // Already wired up for this exact DOM node; avoid double-binding
      // listeners if document$ fires again without a real content swap.
      return;
    }
    wiredContainer = container;

    const sourceInput = container.querySelector("#playground-source");
    const outputEl = container.querySelector("#playground-output");
    const violationsEl = container.querySelector("#playground-violations");
    const statusEl = container.querySelector("#playground-status");
    const runButton = container.querySelector("#playground-run");
    const keepComments = container.querySelector("#playground-keep-comments");
    const keepDocstrings = container.querySelector("#playground-keep-docstrings");
    const keepAnnotations = container.querySelector("#playground-keep-annotations");
    const keepBlank = container.querySelector("#playground-keep-blank");
    const usePass = container.querySelector("#playground-use-pass");

    if (!sourceInput || !outputEl || !violationsEl || !statusEl || !runButton) {
      return;
    }

    function setStatus(text, isError) {
      statusEl.textContent = text;
      statusEl.classList.toggle("playground-status--error", Boolean(isError));
    }

    runButton.disabled = true;

    getPyodide(setStatus)
      .then(() => {
        setStatus("Ready");
        runButton.disabled = false;
      })
      .catch((err) => {
        console.error("[pystrip playground] failed to initialise Pyodide", err);
        setStatus(`Failed to load: ${err.message}`, true);
      });

    runButton.addEventListener("click", async () => {
      runButton.disabled = true;
      setStatus("Running…");

      try {
        const pyodide = await pyodideReadyPromise;
        if (!pyodide) {
          throw new Error("Pyodide is not ready yet.");
        }

        pyodide.globals.set("__playground_source", sourceInput.value);
        pyodide.globals.set("__keep_comments", Boolean(keepComments && keepComments.checked));
        pyodide.globals.set("__keep_docstrings", Boolean(keepDocstrings && keepDocstrings.checked));
        pyodide.globals.set("__keep_annotations", Boolean(keepAnnotations && keepAnnotations.checked));
        pyodide.globals.set("__keep_blank", Boolean(keepBlank && keepBlank.checked));
        pyodide.globals.set("__use_pass", Boolean(usePass && usePass.checked));

        const rawResult = pyodide.runPython(STRIP_SCRIPT);
        const payload = JSON.parse(rawResult);

        if (!payload.ok) {
          throw new Error(payload.error);
        }

        outputEl.textContent = payload.code;

        if (payload.violations.length === 0) {
          violationsEl.innerHTML = "<li>No violations.</li>";
        } else {
          violationsEl.innerHTML = payload.violations
            .map(
              (v) =>
                `<li><code>${v.line}:${v.column}</code> <strong>${escapeHtml(v.rule)}</strong> — ${escapeHtml(v.message)}</li>`
            )
            .join("");
        }

        setStatus("Ready");
      } catch (err) {
        console.error("[pystrip playground] strip failed", err);
        outputEl.textContent = "";
        violationsEl.innerHTML = "";
        setStatus(`Error: ${err.message}`, true);
      } finally {
        runButton.disabled = false;
      }
    });
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    // Material's observable: fires on every page view, including
    // navigation.instant SPA-style transitions.
    window.document$.subscribe(initPlayground);
  } else {
    document.addEventListener("DOMContentLoaded", initPlayground);
  }
})();
