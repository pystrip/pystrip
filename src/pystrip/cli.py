"""Command-line interface for pystrip."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pystrip.cache import CacheEntry, StripCache
from pystrip.config import PyStripConfig, load_config
from pystrip.discovery import find_project_root
from pystrip.reporting import FormatType, format_violations
from pystrip.stripper import StripConfig, StripResult, Violation, strip_code
from pystrip.utils import collect_python_files

console = Console(stderr=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pystrip",
        description="Remove comments and docstrings from Python source files.",
    )
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to process")
    parser.add_argument("--exclude", action="append", default=None, metavar="PATH")
    parser.add_argument("--exclude-glob", action="append", default=None, metavar="PATTERN")
    parser.add_argument("--keep-docstrings", action="store_true", default=None)
    parser.add_argument("--check", action="store_true", help="Don't modify; exit 1 if changes")
    parser.add_argument("--diff", action="store_true", help="Show unified diff")
    parser.add_argument("--in-place", action="store_true", help="Write changes back to files")
    parser.add_argument("--output-dir", type=Path, default=None, metavar="DIR")
    parser.set_defaults(recursive=True)
    parser.add_argument("--no-recursive", dest="recursive", action="store_false")
    parser.add_argument("--jobs", type=int, default=None, metavar="N")
    parser.add_argument("--cache", action="store_true", default=None)
    parser.add_argument("--no-cache", dest="cache", action="store_false")
    parser.add_argument(
        "--keep-blank",
        dest="keep_blank",
        action="store_true",
        default=None,
        help="Keep blank lines introduced by comment removal",
    )
    parser.add_argument("--config", type=Path, default=None, metavar="PATH")
    parser.add_argument(
        "--format",
        choices=["text", "json", "sarif", "gitlab", "github"],
        default=None,
        dest="output_format",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _apply_cli_overrides(cfg: PyStripConfig, args: argparse.Namespace) -> None:
    """Apply CLI argument overrides to configuration."""
    if args.keep_docstrings:
        cfg.remove_docstrings = False
    if args.exclude is not None:
        cfg.exclude = args.exclude
    if args.exclude_glob is not None:
        cfg.exclude_glob = args.exclude_glob
    if args.jobs is not None:
        cfg.jobs = args.jobs
    if args.cache is not None:
        cfg.cache = args.cache
    if getattr(args, "keep_blank", None):
        cfg.remove_blank_lines = False


def _process_file(
    py_file: Path,
    cfg: PyStripConfig,
) -> tuple[Path, StripResult]:
    strip_cfg = StripConfig(
        remove_comments=cfg.remove_comments,
        remove_docstrings=cfg.remove_docstrings,
        remove_blank_lines=cfg.remove_blank_lines,
        filename=str(py_file),
    )
    source = py_file.read_text(encoding="utf-8")
    result = strip_code(source, strip_cfg)
    return py_file, result


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        _run(args)
    except KeyboardInterrupt:
        sys.exit(2)
    except Exception as exc:
        console.print_exception()
        if not args.quiet:
            console.print(f"[red]Error:[/red] {exc}")
        sys.exit(2)


def _run(args: argparse.Namespace) -> None:
    output_format: FormatType = args.output_format or "text"

    # Discover project root
    project_root = find_project_root()

    # Load configuration
    cfg = load_config(project_root, config_path=args.config)

    # Apply CLI overrides
    _apply_cli_overrides(cfg, args)

    # Collect files
    input_paths = [Path(p) for p in args.paths]
    py_files = collect_python_files(
        paths=input_paths,
        recursive=args.recursive,
        exclude=cfg.exclude,
        exclude_glob=cfg.exclude_glob,
    )

    if not py_files:
        if not args.quiet:
            console.print("[yellow]No Python files found.[/yellow]")
        sys.exit(0)

    # Set up cache
    cache: StripCache | None = None
    if cfg.cache:
        cache = StripCache(project_root)

    all_violations: list[Violation] = []
    violations_by_file: dict[str, list[Violation]] = defaultdict(list)
    files_changed = 0

    # Parallel processing
    jobs = max(1, cfg.jobs)

    def process_files(
        files: list[Path],
    ) -> list[tuple[Path, StripResult]]:
        if jobs == 1 or len(files) == 1:
            return [_process_file(f, cfg) for f in files]
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = [executor.submit(_process_file, f, cfg) for f in files]
            return [f.result() for f in futures]

    to_process: list[Path] = []
    skipped_from_cache: list[Path] = []

    for py_file in py_files:
        if cache and cache.is_unchanged(py_file):
            skipped_from_cache.append(py_file)
        else:
            to_process.append(py_file)

    if args.verbose and skipped_from_cache:
        console.print(f"[dim]Skipped {len(skipped_from_cache)} cached file(s).[/dim]")

    # Restore violations from cache for unchanged files so they are always reported
    for py_file in skipped_from_cache:
        if cache:
            cached_entry = cache.read(py_file)
            if cached_entry:
                all_violations.extend(
                    Violation(
                        file=str(v["file"]),
                        line=int(v["line"]),
                        column=int(v["column"]),
                        rule=str(v["rule"]),
                        message=str(v["message"]),
                    )
                    for v in cached_entry.violations
                )
                for v in cached_entry.violations:
                    violations_by_file[str(v["file"])].append(
                        Violation(
                            file=str(v["file"]),
                            line=int(v["line"]),
                            column=int(v["column"]),
                            rule=str(v["rule"]),
                            message=str(v["message"]),
                        )
                    )
                if cached_entry.changed:
                    files_changed += 1

    results: list[tuple[Path, StripResult]] = []

    if to_process:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=args.quiet,
        ) as progress:
            progress.add_task(f"Processing {len(to_process)} file(s)...", total=None)
            results = process_files(to_process)

    for py_file, result in results:
        all_violations.extend(result.violations)
        violations_by_file[str(py_file)].extend(result.violations)

        if result.changed:
            files_changed += 1

            if args.diff:
                import difflib

                original = py_file.read_text(encoding="utf-8")
                diff = difflib.unified_diff(
                    original.splitlines(keepends=True),
                    result.modified_code.splitlines(keepends=True),
                    fromfile=str(py_file),
                    tofile=str(py_file),
                )
                sys.stdout.writelines(diff)

            if args.in_place and not args.check:
                py_file.write_text(result.modified_code, encoding="utf-8")
            elif args.output_dir is not None and not args.check:
                out = args.output_dir / py_file.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(result.modified_code, encoding="utf-8")

        if cache:
            import hashlib

            sha256 = hashlib.sha256(py_file.read_bytes()).hexdigest()
            cache.write(
                py_file,
                CacheEntry(
                    sha256=sha256,
                    changed=result.changed,
                    violations=[
                        {
                            "file": v.file,
                            "line": v.line,
                            "column": v.column,
                            "rule": v.rule,
                            "message": v.message,
                        }
                        for v in result.violations
                    ],
                ),
            )

    if args.verbose and all_violations:
        for violation in all_violations:
            if violation.rule != "COMMENT_REMOVED":
                continue
            sys.stderr.write(
                f"{violation.file}:{violation.line}:{violation.column} {violation.message}\n"
            )

        for file_path, file_violations in sorted(violations_by_file.items()):
            removed_count = sum(1 for v in file_violations if v.rule == "COMMENT_REMOVED")
            if removed_count:
                sys.stderr.write(f"{file_path}: removed {removed_count} comment(s).\n")

    # Output violations
    if all_violations:
        output = format_violations(all_violations, fmt=output_format)
        if output:
            print(output)

    # Summary
    if not args.quiet:
        if files_changed:
            console.print(
                f"[bold]{'Would change' if args.check else 'Changed'}[/bold] "
                f"{files_changed} file(s), "
                f"{len(all_violations)} violation(s)."
            )
        else:
            console.print("[green]All files clean.[/green]")

    if args.check and files_changed:
        sys.exit(1)
