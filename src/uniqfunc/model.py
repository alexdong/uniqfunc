"""Data models for uniqfunc scans.

Usage:
    uv run --env-file .env -m uniqfunc.model -h
"""

import argparse
import logging
import pprint
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FuncRef:
    """Reference to a function definition in a source file.

    Examples:
        >>> FuncRef(Path("example.py"), 1, 1, "demo", "def demo():", [], None, None, []).name
        'demo'
    """

    path: Path
    line: int
    col: int
    name: str
    signature: str
    params: list[str] = field(default_factory=list)
    returns: str | None = None
    doc: str | None = None
    ast_fingerprint: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert self.line >= 1, "FuncRef.line must be a 1-based line number."
        assert self.col >= 1, "FuncRef.col must be a 1-based column number."
        assert self.name, "FuncRef.name must be a non-empty function name."
        assert self.signature, "FuncRef.signature must be a non-empty signature."


@dataclass(frozen=True, slots=True)
class ScanError:
    """Operational or parsing error encountered during scanning."""

    code: str
    path: Path
    line: int
    col: int
    message: str

    def __post_init__(self) -> None:
        assert self.code, "ScanError.code must be a non-empty diagnostic code."
        assert self.line >= 1, "ScanError.line must be a 1-based line number."
        assert self.col >= 1, "ScanError.col must be a 1-based column number."
        assert self.message, "ScanError.message must be a non-empty description."


@dataclass(frozen=True, slots=True)
class NamingConflict:
    """Duplicate function name detected across the repo."""

    name: str
    occurrence: FuncRef
    first_seen: FuncRef

    def __post_init__(self) -> None:
        assert self.name, "NamingConflict.name must be a non-empty function name."


@dataclass(frozen=True, slots=True)
class ReuseCandidate:
    """Candidate suggestion for potential reuse."""

    path: Path
    line: int
    col: int
    name: str
    signature: str
    score: float
    signals: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert self.line >= 1, "ReuseCandidate.line must be a 1-based line number."
        assert self.col >= 1, "ReuseCandidate.col must be a 1-based column number."
        assert self.name, "ReuseCandidate.name must be a non-empty function name."
        assert self.signature, "ReuseCandidate.signature must be a non-empty signature."
        assert 0.0 <= self.score <= 1.0, "ReuseCandidate.score must be between 0 and 1."


@dataclass(frozen=True, slots=True)
class ReuseSuggestion:
    """Reuse suggestion for a target function."""

    target: FuncRef
    candidates: list[ReuseCandidate] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Result of scanning a repository for function conflicts and reuse."""

    repo_root: Path
    files: list[Path] = field(default_factory=list)
    functions: list[FuncRef] = field(default_factory=list)
    excluded_functions: list[FuncRef] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    errors: list[ScanError] = field(default_factory=list)
    conflicts: list[NamingConflict] = field(default_factory=list)
    suggestions: list[ReuseSuggestion] = field(default_factory=list)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Inspect uniqfunc data models.")
    parser.add_argument(
        "--show-sample",
        action="store_true",
        help="Print a sample ScanResult for debugging.",
    )
    return parser


def _sample_result() -> ScanResult:
    sample_ref = FuncRef(
        Path("example.py"),
        1,
        1,
        "demo",
        "def demo():",
        [],
        None,
        None,
        [],
    )
    return ScanResult(repo_root=Path.cwd(), functions=[sample_ref])


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.model --show-sample
    """
    parser = build_arg_parser()
    parser.parse_args(argv)
    pprint.pprint(_sample_result())
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
