"""Output formatting for uniqfunc scans.

Usage:
    uv run --env-file .env -m uniqfunc.formatters -h
"""

import argparse
import json
import logging
import pprint
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from uniqfunc import __version__
from uniqfunc.model import (
    FuncRef,
    NamingConflict,
    ReuseCandidate,
    ReuseSuggestion,
    ScanError,
    ScanResult,
)


@dataclass(frozen=True, slots=True)
class TextOutput:
    stdout: str
    stderr: str


def _path_to_string(path: Path) -> str:
    return path.as_posix()


def _format_location(path: Path, line: int, col: int) -> str:
    return f"{_path_to_string(path)}:{line}:{col}"


def _format_error_line(error: ScanError) -> str:
    return f"{_format_location(error.path, error.line, error.col)} {error.code} {error.message}"


def format_error_lines(errors: Sequence[ScanError]) -> list[str]:
    return [_format_error_line(error) for error in errors]


def _format_summary_lines(scan_result: ScanResult) -> list[str]:
    repo_root = _path_to_string(scan_result.repo_root.resolve())
    duplicate_names = {conflict.name for conflict in scan_result.conflicts}
    reuse_candidates = sum(
        len(suggestion.candidates) for suggestion in scan_result.suggestions
    )
    stats = (
        f"files={len(scan_result.files)} "
        f"functions={len(scan_result.functions)} "
        f"excluded_functions={len(scan_result.excluded_functions)} "
        f"duplicate_names={len(duplicate_names)} "
        f"duplicate_occurrences={len(scan_result.conflicts)} "
        f"reuse_targets={len(scan_result.suggestions)} "
        f"reuse_candidates={reuse_candidates} "
        f"errors={len(scan_result.errors)}"
    )
    lines = [f"uniqfunc {__version__} repo_root={repo_root}", stats]
    if scan_result.exclude_patterns:
        patterns = ",".join(scan_result.exclude_patterns)
        lines.append(f"exclude_name_patterns={patterns}")
    return lines


def _format_conflict_line(conflict: NamingConflict) -> str:
    occurrence = conflict.occurrence
    first = conflict.first_seen
    first_location = _format_location(first.path, first.line, first.col)
    return (
        f"{_format_location(occurrence.path, occurrence.line, occurrence.col)} "
        f"UQF100 duplicate function name '{conflict.name}' (also in {first_location}) "
        f"signature={occurrence.signature} "
        f"also_signature={first.signature}"
    )


def _format_score(value: float) -> str:
    return f"{value:.2f}"


def _format_candidate_line(candidate: ReuseCandidate, target: FuncRef) -> str:
    name_token = candidate.signals.get("name_token_jaccard", 0.0)
    signature_score = candidate.signals.get("signature_score", 0.0)
    ast_score = candidate.signals.get("ast_score", 0.0)
    signals = (
        f"name_token_jaccard:{_format_score(name_token)} "
        f"signature:{_format_score(signature_score)} "
        f"ast:{_format_score(ast_score)}"
    )
    target_location = _format_location(target.path, target.line, target.col)
    return (
        f"{_format_location(candidate.path, candidate.line, candidate.col)} "
        f"UQF201 candidate_for={target.name} target_loc={target_location} "
        f"name={candidate.name} score={_format_score(candidate.score)} "
        f"signals={signals} "
        f"signature={candidate.signature}"
    )


def _format_suggestion_lines(suggestions: Sequence[ReuseSuggestion]) -> list[str]:
    if not suggestions:
        return []
    lines = ["=== UNIQFUNC LLM REUSE SUGGESTIONS ==="]
    for suggestion in suggestions:
        target = suggestion.target
        lines.append(
            f"{_format_location(target.path, target.line, target.col)} "
            f"UQF200 reuse_candidate target={target.name} "
            f"candidates={len(suggestion.candidates)} "
            f"signature={target.signature}"
        )
        lines.extend(
            _format_candidate_line(candidate, target)
            for candidate in suggestion.candidates
        )
    lines.append("=== END UNIQFUNC LLM REUSE SUGGESTIONS ===")
    return lines


def format_text(scan_result: ScanResult) -> TextOutput:
    summary_lines = _format_summary_lines(scan_result)
    conflict_lines = [
        _format_conflict_line(conflict) for conflict in scan_result.conflicts
    ]
    suggestion_lines = _format_suggestion_lines(scan_result.suggestions)
    stdout_lines = [*summary_lines, *conflict_lines, *suggestion_lines]
    stderr_lines = format_error_lines(scan_result.errors)
    stdout = "\n".join(stdout_lines)
    stderr = "\n".join(stderr_lines)
    return TextOutput(stdout=stdout, stderr=stderr)


def _func_ref_location(func_ref: FuncRef) -> dict[str, object]:
    return {
        "path": _path_to_string(func_ref.path),
        "line": func_ref.line,
        "col": func_ref.col,
    }


def _func_ref_identity(func_ref: FuncRef) -> dict[str, object]:
    return {
        "path": _path_to_string(func_ref.path),
        "line": func_ref.line,
        "col": func_ref.col,
        "name": func_ref.name,
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
        "target": _func_ref_identity(suggestion.target),
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
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Format uniqfunc scan results.")
    parser.add_argument(
        "--show-sample",
        action="store_true",
        help="Print a sample formatted output.",
    )
    return parser


def _sample_result() -> ScanResult:
    return ScanResult(repo_root=Path.cwd())


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.formatters --show-sample
    """
    parser = build_arg_parser()
    parser.parse_args(argv)
    pprint.pprint(format_text(_sample_result()))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
