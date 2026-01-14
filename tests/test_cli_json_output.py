import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from uniqfunc.cli import main

EXIT_CONFLICT = 1


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


def test_json_output_schema(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_path = tmp_path / "repo"
    _init_repo(repo_path)
    (repo_path / "a.py").write_text("def dup():\n    return 1\n", encoding="utf-8")
    (repo_path / "b.py").write_text("def dup():\n    return 2\n", encoding="utf-8")
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
    _run_git(repo_path, ["add", "a.py", "b.py", "c.py"])
    _run_git(repo_path, ["commit", "-m", "Add sample functions"])

    exit_code = main(["--format", "json", str(repo_path)])
    assert exit_code == EXIT_CONFLICT
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["version"] == "0.1.3"
    assert payload["repo_root"] == repo_path.as_posix()
    assert set(payload.keys()) == {
        "version",
        "repo_root",
        "naming_conflicts",
        "reuse_suggestions",
        "errors",
    }
    conflicts = payload["naming_conflicts"]
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["code"] == "UQF100"
    assert conflict["name"] == "dup"
    assert conflict["occurrence"]["path"] == "b.py"
    assert conflict["first_seen"]["path"] == "a.py"

    suggestions = payload["reuse_suggestions"]
    assert any(suggestion["target"]["name"] == "clamp" for suggestion in suggestions)
    clamp_suggestion = next(
        suggestion
        for suggestion in suggestions
        if suggestion["target"]["name"] == "clamp"
    )
    assert clamp_suggestion["candidates"]
    candidate = clamp_suggestion["candidates"][0]
    assert {"path", "line", "col", "name", "score", "signals"} <= candidate.keys()
    assert payload["errors"] == []
