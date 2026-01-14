# CONTEXT

## Purpose

uniqfunc is a git-aware Python CLI that enforces globally unique function names (blocking) and emits reuse candidates for agent review (non-blocking).

## Entry points

- `uv run --env-file .env -m uniqfunc.cli -h`
- `uvx uniqfunc`

## Core modules

- `src/uniqfunc/model.py`: dataclasses for `FuncRef`, `ScanError`, `NamingConflict`, `ReuseSuggestion`, and `ScanResult`.
- `src/uniqfunc/git_files.py`: git repo root resolution and Python file selection via `git ls-files`.
- `src/uniqfunc/parser.py`: AST parsing, function extraction (nested/methods), docstrings, annotations, UQF001 handling.
- `src/uniqfunc/fingerprint.py`: canonical token fingerprints and shingles.
- `src/uniqfunc/similarity_name_signature.py`: name/signature scoring helpers.
- `src/uniqfunc/similarity_ast.py`: AST shingle and multiset similarity.
- `src/uniqfunc/similarity.py`: combines scores, thresholds, top-k ranking.
- `src/uniqfunc/formatters.py`: text (UQF100/UQF200/UQF201) and JSON output formatting.
- `src/uniqfunc/logging_config.py`: run log setup in `run/*.log`.

## Diagnostics and exit codes

- Errors: `UQF000` (read), `UQF001` (syntax), `UQF002` (git failure), `UQF003` (git missing).
- Conflicts: `UQF100` duplicate function name.
- Suggestions: `UQF200` target summary, `UQF201` candidate detail (text mode).

Exit codes: `0` (no conflicts), `1` (conflicts), `2` (fatal git error).

## Tests

- Unit tests live in `tests/`, including parser, fingerprint, similarity, and CLI text/JSON output.
