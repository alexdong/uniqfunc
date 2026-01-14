"""Git-aware file discovery for uniqfunc.

Usage:
    uv run --env-file .env -m uniqfunc.git_files -h
"""

import argparse
import logging
import pprint
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from uniqfunc.model import ScanError

logger = logging.getLogger(__name__)

GIT_MISSING_CODE = "UQF003"
GIT_FAILED_CODE = "UQF002"


@dataclass(frozen=True, slots=True)
class RepoRootOutcome:
    repo_root: Path


@dataclass(frozen=True, slots=True)
class RepoRootFailure:
    error: ScanError


RepoRootResult = RepoRootOutcome | RepoRootFailure


@dataclass(frozen=True, slots=True)
class FileListOutcome:
    repo_root: Path
    files: list[Path]


@dataclass(frozen=True, slots=True)
class FileListFailure:
    error: ScanError


FileListResult = FileListOutcome | FileListFailure


def _build_git_missing_error(cwd: Path) -> ScanError:
    return ScanError(
        code=GIT_MISSING_CODE,
        path=cwd,
        line=1,
        col=1,
        message="git executable not found on PATH.",
    )


def _build_git_failed_error(cwd: Path, stderr: str) -> ScanError:
    detail = stderr.strip() or "git command failed."
    return ScanError(
        code=GIT_FAILED_CODE,
        path=cwd,
        line=1,
        col=1,
        message=detail,
    )


def resolve_repo_root(cwd: Path) -> RepoRootResult:
    assert cwd.is_dir(), "resolve_repo_root expects an existing directory."
    logger.debug("Resolving git repo root from %s", cwd)
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return RepoRootFailure(error=_build_git_missing_error(cwd))
    if completed.returncode != 0:
        return RepoRootFailure(error=_build_git_failed_error(cwd, completed.stderr))
    repo_root = Path(completed.stdout.strip())
    logger.debug("Resolved git repo root as %s", repo_root)
    return RepoRootOutcome(repo_root=repo_root)


def list_python_files(repo_root: Path) -> FileListResult:
    assert repo_root.is_dir(), "list_python_files expects a directory repo root."
    logger.debug("Listing Python files in %s", repo_root)
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                "*.py",
            ],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return FileListFailure(error=_build_git_missing_error(repo_root))
    if completed.returncode != 0:
        return FileListFailure(
            error=_build_git_failed_error(
                repo_root, completed.stderr.decode("utf-8", errors="replace")
            )
        )
    entries = completed.stdout.split(b"\x00")
    files: list[Path] = []
    for entry in entries:
        if not entry:
            continue
        path = Path(entry.decode("utf-8", errors="replace"))
        files.append(path)
    files.sort(key=lambda item: item.as_posix())
    logger.debug("Discovered %s Python files", len(files))
    return FileListOutcome(repo_root=repo_root, files=files)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="List Python files tracked by git.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path inside the git repository.",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.git_files .
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    cwd = Path(args.path).resolve()
    root_result = resolve_repo_root(cwd)
    if isinstance(root_result, RepoRootFailure):
        pprint.pprint(root_result.error)
        return 2
    files_result = list_python_files(root_result.repo_root)
    if isinstance(files_result, FileListFailure):
        pprint.pprint(files_result.error)
        return 2
    pprint.pprint(files_result.files)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
