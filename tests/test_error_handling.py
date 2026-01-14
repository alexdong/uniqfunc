import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

import uniqfunc.git_files
from uniqfunc.cli import main

EXIT_OK = 0
EXIT_FATAL = 2


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


def _parse_errors(output: str) -> list[dict[str, object]]:
    payload = json.loads(output)
    errors = payload["errors"]
    assert isinstance(errors, list)
    return errors


def test_cli_reports_unreadable_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    unreadable = repo_path / "unreadable.py"
    unreadable.write_text("def demo():\n    return 1\n", encoding="utf-8")
    _run_git(repo_path, ["add", "unreadable.py"])
    _run_git(repo_path, ["commit", "-m", "Add unreadable file"])
    unreadable.chmod(0)
    try:
        exit_code = main(["--format", "json", str(repo_path)])
    finally:
        unreadable.chmod(0o644)
    assert exit_code == EXIT_OK
    output = capsys.readouterr().out
    errors = _parse_errors(output)
    assert any(error["code"] == "UQF000" for error in errors)


def test_cli_reports_syntax_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    bad_file = repo_path / "bad.py"
    bad_file.write_text("def broken(:\n    return 1\n", encoding="utf-8")
    exit_code = main(["--format", "json", str(repo_path)])
    assert exit_code == EXIT_OK
    output = capsys.readouterr().out
    errors = _parse_errors(output)
    assert any(error["code"] == "UQF001" for error in errors)


def test_cli_reports_not_git_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["--format", "json", str(tmp_path)])
    assert exit_code == EXIT_FATAL
    output = capsys.readouterr().out
    errors = _parse_errors(output)
    assert any(error["code"] == "UQF002" for error in errors)


def test_cli_reports_git_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(uniqfunc.git_files.subprocess, "run", _raise_missing)
    exit_code = main(["--format", "json", str(tmp_path)])
    assert exit_code == EXIT_FATAL
    output = capsys.readouterr().out
    errors = _parse_errors(output)
    assert any(error["code"] == "UQF003" for error in errors)
