import subprocess
from collections.abc import Sequence
from pathlib import Path

from uniqfunc.git_files import (
    FileListOutcome,
    RepoRootOutcome,
    list_python_files,
    resolve_repo_root,
)


def _run_git(repo_path: Path, args: Sequence[str]) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, (
        f"git {' '.join(args)} failed: {completed.stdout}\n{completed.stderr}"
    )


def _init_repo(repo_path: Path) -> None:
    repo_path.mkdir()
    _run_git(repo_path, ["init"])
    _run_git(repo_path, ["config", "user.email", "tests@example.com"])
    _run_git(repo_path, ["config", "user.name", "Tests"])


def test_git_selection_includes_tracked_and_untracked(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)

    tracked = repo_path / "tracked.py"
    tracked.write_text("def tracked():\n    return 1\n", encoding="utf-8")
    untracked = repo_path / "untracked.py"
    untracked.write_text("def untracked():\n    return 2\n", encoding="utf-8")
    ignored = repo_path / "ignored.py"
    ignored.write_text("def ignored():\n    return 3\n", encoding="utf-8")
    gitignore = repo_path / ".gitignore"
    gitignore.write_text("ignored.py\n", encoding="utf-8")

    _run_git(repo_path, ["add", "tracked.py", ".gitignore"])
    _run_git(repo_path, ["commit", "-m", "Add tracked files"])

    root_result = resolve_repo_root(repo_path)
    assert isinstance(root_result, RepoRootOutcome)

    files_result = list_python_files(root_result.repo_root)
    assert isinstance(files_result, FileListOutcome)

    assert files_result.files == [Path("tracked.py"), Path("untracked.py")]
