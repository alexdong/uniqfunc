"""Uniqfunc CLI entry point.

Usage:
    uv run --env-file .env -m uniqfunc.cli -h
    uv run --env-file .env -m uniqfunc.cli --format json
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from uniqfunc import __version__
from uniqfunc.git_files import (
    FileListFailure,
    RepoRootFailure,
    list_python_files,
    resolve_repo_root,
)
from uniqfunc.logging_config import configure_logging
from uniqfunc.model import (
    FuncRef,
    NamingConflict,
    ReuseCandidate,
    ReuseSuggestion,
    ScanError,
    ScanResult,
)
from uniqfunc.parser import ParseFailure, parse_function_defs
from uniqfunc.similarity import reuse_suggestions

logger = logging.getLogger(__name__)

READ_ERROR_CODE = "UQF000"


@dataclass(frozen=True, slots=True)
class ReadOutcome:
    path: Path
    source: str


@dataclass(frozen=True, slots=True)
class ReadFailure:
    error: ScanError


ReadResult = ReadOutcome | ReadFailure


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


def scan_repository(cwd: Path, similarity_threshold: float) -> ScanResult | ScanError:
    root_result = resolve_repo_root(cwd)
    if isinstance(root_result, RepoRootFailure):
        return root_result.error
    files_result = list_python_files(root_result.repo_root)
    if isinstance(files_result, FileListFailure):
        return files_result.error
    scan_slice = _scan_files(root_result.repo_root, files_result.files)
    suggestions = reuse_suggestions(scan_slice.functions, similarity_threshold)
    return ScanResult(
        repo_root=root_result.repo_root,
        functions=scan_slice.functions,
        errors=scan_slice.errors,
        suggestions=suggestions,
    )


def _path_to_string(path: Path) -> str:
    return path.as_posix()


def _func_ref_location(func_ref: FuncRef) -> dict[str, object]:
    return {
        "path": _path_to_string(func_ref.path),
        "line": func_ref.line,
        "col": func_ref.col,
    }


def _naming_conflict_json(conflict: NamingConflict) -> dict[str, object]:
    return {
        "code": "UQF100",
        "name": conflict.name,
        "occurrence": _func_ref_location(conflict.occurrence),
        "first_seen": _func_ref_location(conflict.first_seen),
    }


def _reuse_candidate_json(candidate: ReuseCandidate) -> dict[str, object]:
    return {
        "path": _path_to_string(candidate.path),
        "line": candidate.line,
        "col": candidate.col,
        "name": candidate.name,
        "score": candidate.score,
        "signals": candidate.signals,
    }


def _reuse_suggestion_json(suggestion: ReuseSuggestion) -> dict[str, object]:
    return {
        "target": {
            "path": _path_to_string(suggestion.target.path),
            "line": suggestion.target.line,
            "col": suggestion.target.col,
            "name": suggestion.target.name,
        },
        "candidates": [
            _reuse_candidate_json(candidate) for candidate in suggestion.candidates
        ],
    }


def _scan_error_json(error: ScanError) -> dict[str, object]:
    return {
        "code": error.code,
        "path": _path_to_string(error.path),
        "line": error.line,
        "col": error.col,
        "message": error.message,
    }


def format_json(scan_result: ScanResult) -> str:
    payload = {
        "version": __version__,
        "repo_root": _path_to_string(scan_result.repo_root.resolve()),
        "naming_conflicts": [
            _naming_conflict_json(conflict) for conflict in scan_result.conflicts
        ],
        "reuse_suggestions": [
            _reuse_suggestion_json(suggestion) for suggestion in scan_result.suggestions
        ],
        "errors": [_scan_error_json(error) for error in scan_result.errors],
    }
    return json.dumps(payload, indent=2)


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
    return parser


def main(argv: Sequence[str]) -> int:
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
    scan_outcome = scan_repository(cwd, args.similarity_threshold)
    if isinstance(scan_outcome, ScanError):
        result = ScanResult(repo_root=cwd, errors=[scan_outcome])
        output = format_json(result)
        print(output)
        return 2
    output = format_json(scan_outcome)
    print(output)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
