"""Uniqfunc CLI entry point.

Usage:
    uv run --env-file .env -m uniqfunc.cli -h
    uv run --env-file .env -m uniqfunc.cli --format json
    uv run --env-file .env -m uniqfunc.cli --exclude-name '^main$' .
"""

import argparse
import logging
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from uniqfunc import __version__
from uniqfunc.formatters import format_error_lines, format_json, format_text
from uniqfunc.git_files import (
    FileListFailure,
    RepoRootFailure,
    list_python_files,
    resolve_repo_root,
)
from uniqfunc.logging_config import configure_logging
from uniqfunc.model import FuncRef, NamingConflict, ScanError, ScanResult
from uniqfunc.parser import ParseFailure, parse_function_defs
from uniqfunc.similarity import reuse_suggestions

logger = logging.getLogger(__name__)

READ_ERROR_CODE = "UQF000"
FATAL_ERROR_CODES = {"UQF002", "UQF003"}


@dataclass(frozen=True, slots=True)
class ReadOutcome:
    path: Path
    source: str


@dataclass(frozen=True, slots=True)
class ReadFailure:
    error: ScanError


ReadResult = ReadOutcome | ReadFailure


@dataclass(frozen=True, slots=True)
class NamePattern:
    raw: str
    regex: re.Pattern[str]

    def matches(self, name: str) -> bool:
        return self.regex.search(name) is not None


def _compile_name_pattern(raw: str) -> NamePattern:
    assert raw, "exclude name pattern must be non-empty."
    try:
        regex = re.compile(raw)
    except re.error as exc:
        raise argparse.ArgumentTypeError(
            f"invalid regex for --exclude-name: {raw} ({exc})"
        ) from exc
    return NamePattern(raw=raw, regex=regex)


DEFAULT_EXCLUDE_PATTERNS = (
    _compile_name_pattern("^main$"),
    _compile_name_pattern("^cli$"),
)


def _dedupe_patterns(patterns: Sequence[NamePattern]) -> list[NamePattern]:
    seen: set[str] = set()
    unique: list[NamePattern] = []
    for pattern in patterns:
        if pattern.raw in seen:
            continue
        unique.append(pattern)
        seen.add(pattern.raw)
    return unique


def read_source(repo_root: Path, relative_path: Path) -> ReadResult:
    file_path = repo_root / relative_path
    if not file_path.is_file():
        return ReadFailure(
            error=ScanError(
                code=READ_ERROR_CODE,
                path=relative_path,
                line=1,
                col=1,
                message="file path does not exist or is not a file.",
            ),
        )
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return ReadFailure(
            error=ScanError(
                code=READ_ERROR_CODE,
                path=relative_path,
                line=1,
                col=1,
                message=str(exc),
            ),
        )
    return ReadOutcome(path=relative_path, source=source)


@dataclass(frozen=True, slots=True)
class ScanSlice:
    functions: list[FuncRef]
    errors: list[ScanError]


@dataclass(frozen=True, slots=True)
class ExclusionOutcome:
    included: list[FuncRef]
    excluded: list[FuncRef]


def _apply_exclusions(
    functions: Sequence[FuncRef],
    patterns: Sequence[NamePattern],
) -> ExclusionOutcome:
    if not patterns:
        return ExclusionOutcome(included=list(functions), excluded=[])
    included: list[FuncRef] = []
    excluded: list[FuncRef] = []
    for func in functions:
        if any(pattern.matches(func.name) for pattern in patterns):
            excluded.append(func)
            continue
        included.append(func)
    logger.debug(
        "Excluded %s functions using %s patterns",
        len(excluded),
        len(patterns),
    )
    return ExclusionOutcome(included=included, excluded=excluded)


def _scan_files(repo_root: Path, files: Sequence[Path]) -> ScanSlice:
    functions: list[FuncRef] = []
    errors: list[ScanError] = []
    for rel_path in files:
        read_result = read_source(repo_root, rel_path)
        if isinstance(read_result, ReadFailure):
            errors.append(read_result.error)
            continue
        parse_result = parse_function_defs(read_result.source, read_result.path)
        if isinstance(parse_result, ParseFailure):
            errors.append(parse_result.error)
            continue
        functions.extend(parse_result.functions)
    return ScanSlice(functions=functions, errors=errors)


def find_naming_conflicts(functions: Sequence[FuncRef]) -> list[NamingConflict]:
    ordered = sorted(
        functions,
        key=lambda func: (func.path.as_posix(), func.line, func.name),
    )
    seen: dict[str, FuncRef] = {}
    conflicts: list[NamingConflict] = []
    for func in ordered:
        if func.name in seen:
            conflicts.append(
                NamingConflict(
                    name=func.name,
                    occurrence=func,
                    first_seen=seen[func.name],
                ),
            )
            continue
        seen[func.name] = func
    return conflicts


def is_fatal_error(error: ScanError) -> bool:
    """Return True when an error should terminate the scan.

    Examples:
        >>> is_fatal_error(ScanError("UQF002", Path("repo"), 1, 1, "git error"))
        True
        >>> is_fatal_error(ScanError("UQF000", Path("file.py"), 1, 1, "read error"))
        False
    """
    return error.code in FATAL_ERROR_CODES


def scan_repository(
    cwd: Path,
    similarity_threshold: float,
    exclude_patterns: Sequence[NamePattern],
) -> ScanResult | ScanError:
    root_result = resolve_repo_root(cwd)
    if isinstance(root_result, RepoRootFailure):
        return root_result.error
    files_result = list_python_files(root_result.repo_root)
    if isinstance(files_result, FileListFailure):
        return files_result.error
    scan_slice = _scan_files(root_result.repo_root, files_result.files)
    exclusions = _apply_exclusions(scan_slice.functions, exclude_patterns)
    conflicts = find_naming_conflicts(exclusions.included)
    suggestions = reuse_suggestions(exclusions.included, similarity_threshold)
    return ScanResult(
        repo_root=root_result.repo_root,
        files=files_result.files,
        functions=exclusions.included,
        excluded_functions=exclusions.excluded,
        exclude_patterns=[pattern.raw for pattern in exclude_patterns],
        errors=scan_slice.errors,
        conflicts=conflicts,
        suggestions=suggestions,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect duplicate function names.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to scan (defaults to current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.70,
        help="Minimum similarity score for reuse candidates.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the uniqfunc version and exit.",
    )
    parser.add_argument(
        "--exclude-name",
        action="append",
        default=list(DEFAULT_EXCLUDE_PATTERNS),
        type=_compile_name_pattern,
        help="Regex pattern for function names to ignore (repeatable; defaults to ^main$, ^cli$).",
    )
    return parser


def _emit_text(scan_result: ScanResult) -> None:
    output = format_text(scan_result)
    if output.stdout:
        print(output.stdout)
    if output.stderr:
        print(output.stderr, file=sys.stderr)


def _emit_json(scan_result: ScanResult) -> None:
    print(format_json(scan_result))
    if scan_result.errors:
        for line in format_error_lines(scan_result.errors):
            print(line, file=sys.stderr)


def _emit_output(scan_result: ScanResult, output_format: str) -> None:
    if output_format == "json":
        _emit_json(scan_result)
        return
    _emit_text(scan_result)


# The console script wrapper calls main() without arguments and we observed
# `TypeError: main() missing 1 required positional argument: 'argv'` during
# `uvx uniqfunc --version`; the root cause was a required argv parameter despite
# the wrapper behavior, so we default to an empty tuple to match entrypoint
# semantics while keeping explicit argv for tests and callers.
def main(argv: Sequence[str] = ()) -> int:
    """Run the uniqfunc CLI.

    Examples:
        $ uv run --env-file .env -m uniqfunc.cli --format json
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    configure_logging(Path("run"))
    cwd = Path(args.path).resolve()
    logger.debug("Starting scan in %s", cwd)
    exclude_patterns = _dedupe_patterns(args.exclude_name)
    scan_outcome = scan_repository(
        cwd,
        args.similarity_threshold,
        exclude_patterns,
    )
    if isinstance(scan_outcome, ScanError):
        result = ScanResult(
            repo_root=cwd,
            errors=[scan_outcome],
            exclude_patterns=[pattern.raw for pattern in exclude_patterns],
        )
        _emit_output(result, args.format)
        return 2 if is_fatal_error(scan_outcome) else 0
    _emit_output(scan_outcome, args.format)
    return 1 if scan_outcome.conflicts else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
