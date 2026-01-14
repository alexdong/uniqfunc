import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from uniqfunc import __version__
from uniqfunc.cli import main

EXIT_CONFLICT = 1
EXIT_OK = 0


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


def _is_clickable(line: str) -> bool:
    return re.match(r"^[^:]+:\d+:\d+ ", line) is not None


def _parse_summary_stats(line: str) -> dict[str, str]:
    stats: dict[str, str] = {}
    for part in line.split():
        key, value = part.split("=", 1)
        stats[key] = value
    return stats


def test_text_output_includes_summary_header(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "a.py").write_text("def solo():\n    return 1\n", encoding="utf-8")
    _run_git(repo_path, ["add", "a.py"])
    _run_git(repo_path, ["commit", "-m", "Add solo function"])

    exit_code = main(["--format", "text", str(repo_path)])
    assert exit_code == EXIT_OK
    stdout = capsys.readouterr().out
    lines = stdout.splitlines()
    assert lines[0] == f"uniqfunc {__version__} repo_root={repo_path.as_posix()}"
    stats = _parse_summary_stats(lines[1])
    assert stats["files"] == "1"
    assert stats["functions"] == "1"
    assert stats["excluded_functions"] == "0"
    assert stats["duplicate_names"] == "0"
    assert stats["duplicate_occurrences"] == "0"
    assert stats["reuse_targets"] == "0"
    assert stats["reuse_candidates"] == "0"
    assert stats["errors"] == "0"
    assert lines[2] == "exclude_name_patterns=^main$,^cli$"


def test_text_output_reports_conflicts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "a.py").write_text("def dup():\n    return 1\n", encoding="utf-8")
    (repo_path / "b.py").write_text("def dup():\n    return 2\n", encoding="utf-8")
    _run_git(repo_path, ["add", "a.py", "b.py"])
    _run_git(repo_path, ["commit", "-m", "Add duplicates"])

    exit_code = main(["--format", "text", str(repo_path)])
    assert exit_code == EXIT_CONFLICT
    stdout = capsys.readouterr().out
    conflict_lines = [line for line in stdout.splitlines() if "UQF100" in line]
    assert conflict_lines == [
        "b.py:1:1 UQF100 duplicate function name 'dup' (also in a.py:1:1) "
        "signature=def dup(): also_signature=def dup():",
    ]
    assert _is_clickable(conflict_lines[0])


def test_text_output_reports_suggestions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "c.py").write_text(
        "\n".join(
            [
                "def clamp(x: int, lo: int, hi: int) -> int:",
                "    if x < lo:",
                "        return lo",
                "    if x > hi:",
                "        return hi",
                "    return x",
                "",
                "def clamp_value(value: int, minimum: int, maximum: int) -> int:",
                "    if value < minimum:",
                "        return minimum",
                "    if value > maximum:",
                "        return maximum",
                "    return value",
                "",
            ],
        ),
        encoding="utf-8",
    )

    exit_code = main(["--format", "text", str(repo_path)])
    assert exit_code == EXIT_OK
    stdout = capsys.readouterr().out
    assert "=== UNIQFUNC LLM REUSE SUGGESTIONS ===" in stdout
    assert "=== END UNIQFUNC LLM REUSE SUGGESTIONS ===" in stdout
    lines = [
        line for line in stdout.splitlines() if "UQF200" in line or "UQF201" in line
    ]
    assert lines
    for line in lines:
        assert _is_clickable(line)
    assert any("UQF200" in line and "signature=" in line for line in lines)
    for line in lines:
        if "UQF201" in line:
            assert "signature=" in line
            assert "target_loc=" in line


def test_text_output_excludes_default_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "a.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (repo_path / "b.py").write_text("def cli():\n    return 2\n", encoding="utf-8")
    _run_git(repo_path, ["add", "a.py", "b.py"])
    _run_git(repo_path, ["commit", "-m", "Add default excluded names"])

    exit_code = main(["--format", "text", str(repo_path)])
    assert exit_code == EXIT_OK
    stdout = capsys.readouterr().out
    assert "UQF100" not in stdout
    lines = stdout.splitlines()
    stats = _parse_summary_stats(lines[1])
    assert stats["functions"] == "0"
    assert stats["excluded_functions"] == "2"
    assert lines[2] == "exclude_name_patterns=^main$,^cli$"


def test_text_output_excludes_name_patterns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "a.py").write_text("def skip_me():\n    return 1\n", encoding="utf-8")
    (repo_path / "b.py").write_text("def skip_me():\n    return 2\n", encoding="utf-8")
    _run_git(repo_path, ["add", "a.py", "b.py"])
    _run_git(repo_path, ["commit", "-m", "Add custom excluded names"])

    exit_code = main(
        ["--format", "text", "--exclude-name", "^skip_me$", str(repo_path)]
    )
    assert exit_code == EXIT_OK
    stdout = capsys.readouterr().out
    assert "UQF100" not in stdout
    lines = stdout.splitlines()
    stats = _parse_summary_stats(lines[1])
    assert stats["functions"] == "0"
    assert stats["excluded_functions"] == "2"
    assert lines[2] == "exclude_name_patterns=^main$,^cli$,^skip_me$"
