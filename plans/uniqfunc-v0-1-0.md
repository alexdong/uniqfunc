---
name: uniqfunc-v0-1-0
description: Implement the uniqfunc CLI with git-aware scanning, duplicate detection, reuse suggestions, and tests per SPEC.
---

# Plan

Deliver a stdlib-only Python 3.12+ CLI that scans a git repo for duplicate function names (blocking) and emits deterministic reuse suggestions (non-blocking). The implementation will build explicit data models first, then wire git-aware file selection, AST parsing, fingerprinting, similarity scoring (split into name/signature and AST strategy modules), and output formatting for both text and JSON modes.

The plan prioritizes deterministic output, strict error codes, and VS Code-clickable diagnostics. Tests will be extensive, covering git selection, parsing, error handling, similarity scoring, and output formatting. Packaging and docs will be updated to align with the SPEC requirements, including Hatchling metadata, README examples, and CLI entry points.

## Requirements

- Stdlib-only runtime dependencies with Python >= 3.12 syntax and typing.
- Git-aware file selection using `git ls-files -z --cached --others --exclude-standard -- '*.py'`.
- Duplicate function detection across all defs (top-level, nested, methods) with exit code 1 when conflicts exist.
- Reuse suggestion scoring that is deterministic, stable, and emits top-5 candidates with signals.
- Similarity threshold is configurable via a CLI input argument (default 0.70) and threaded into scoring.
- Text output is VS Code-clickable (each diagnostic line begins with `path:line:col`).
- JSON output emits a single object with stable ordering and all required fields.
- Extensive pytest coverage matching the SPEC acceptance cases.
- Favor function-level doctests as primary executable examples; rely on unit tests for multi-function behavior, determinism, and git/FS interactions that doctests cannot isolate cleanly.

## Scope

- In: core scanning, similarity scoring, CLI, formatting, error handling, tests, packaging, and README updates per SPEC.
- Out: non-Python language support, config files, runtime dependencies, and optional integrations.
- Assumptions: Python version is 3.12+ per SPEC.

## Files and entry points

- `src/uniqfunc/__init__.py`: package metadata, version, and exported symbols indicating public API.
- `src/uniqfunc/cli.py`: argparse CLI entry point, output formatting dispatch, exit codes, and logging setup.

  Usage docstring (when needed):

  ```python
  """Uniqfunc CLI entry point.

  Usage:
      uv run --env-file .env -m uniqfunc.cli -h
      uv run --env-file .env -m uniqfunc.cli --format json
  """
  ```

- `src/uniqfunc/logging_config.py`: stdlib logging configuration that writes run logs to `run/*.log`.
- `src/uniqfunc/git_files.py`: git-aware file selection and repo root resolution.
- `src/uniqfunc/model.py`: dataclasses and typed records for scan output and diagnostics.

  Public functions (include doctests immediately after the signature):

  ```python
  def parse_function_defs(source: str, path: str) -> list[FuncRef]:
      """Parse function defs from a Python source string.

      Examples:
          >>> parse_function_defs("def foo():\n    return 1\n", "a.py")[0].name
          'foo'
      """
  ```

- `src/uniqfunc/parser.py`: AST parsing, function extraction, and error capture.
- `src/uniqfunc/fingerprint.py`: canonical token stream and shingling helpers.
- `src/uniqfunc/similarity_name_signature.py`: name + signature similarity scoring helpers.
- `src/uniqfunc/similarity_ast.py`: AST fingerprint similarity scoring helpers.
- `src/uniqfunc/similarity.py`: combines per-strategy scores and ranks candidates.
- `src/uniqfunc/formatters.py`: text and JSON output formatting (VS Code-clickable diagnostics).
- `tests/test_git_file_selection.py`: git-aware file selection tests.
- `tests/test_error_handling.py`: UQF000/UQF001/UQF002/UQF003 coverage.
- `tests/test_parser.py`: parser extraction and syntax error handling tests.
- `tests/test_fingerprint.py`: fingerprint normalization and shingling tests.
- `tests/test_similarity.py`: similarity scoring tests.
- `tests/test_cli_text_output.py`: text formatting and ordering tests.
- `tests/test_cli_json_output.py`: JSON output schema and stability tests.
- `README.md`: usage, agent loop, VS Code integration, output examples.
- `pyproject.toml`: Hatchling metadata, scripts, and pytest config aligned with SPEC.
- `Makefile`: update targets to match new module and tooling expectations.
- `CONTEXT.md`: regenerate after public API or module layout changes.

## Data model / API changes

- `FuncRef(path: Path, line: int, col: int, name: str, params: list[str], returns: str | None, doc: str | None, ast_fingerprint: list[str])`
- `ScanError(code: str, path: Path, line: int, col: int, message: str)`
- `NamingConflict(name: str, occurrence: FuncRef, first_seen: FuncRef)`
- `ReuseCandidate(path: Path, line: int, col: int, name: str, score: float, signals: dict[str, float])`
- `ReuseSuggestion(target: FuncRef, candidates: list[ReuseCandidate])`
- `ScanResult(repo_root: Path, functions: list[FuncRef], errors: list[ScanError], conflicts: list[NamingConflict], suggestions: list[ReuseSuggestion])`

## Action items

  [ ] 1. Build core models and git-aware file selection with error handling and tests.
  [ ] 2. Implement AST parsing in `parser.py` with doctests and unit tests.
  [ ] 3. Implement fingerprinting in `fingerprint.py` with doctests and unit tests.
  [ ] 4. Implement similarity scoring with per-strategy modules and a combined ranker, using doctests and unit tests.
  [ ] 5. Wire duplicate detection, output formatting, and CLI entry points with tests.
  [ ] 6. Update packaging metadata, README, Makefile, and regenerate CONTEXT.md.

## Task 1: Core models and git-aware file selection

  Goal: Establish the data model and deterministic file discovery with robust error reporting.

- [ ] 1.1 Create `src/uniqfunc` package skeleton and `model.py` dataclasses with doctests.
- [ ] 1.2 Implement `logging_config.py` with run log creation and DEBUG defaults for `__main__` blocks.
- [ ] 1.3 Implement `git_files.py` to run the required `git ls-files` command, capture UQF002/UQF003, and return a stable, sorted list of `Path` objects plus repo root.
- [ ] 1.4 Add file reading helpers that return UQF000 for unreadable files and integrate them into a minimal scan loop.
- [ ] 1.5 Write `tests/test_git_file_selection.py` and `tests/test_error_handling.py` to validate git selection and error codes.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format json`
    Expected: Emits valid JSON with empty `naming_conflicts`/`reuse_suggestions` in a clean repo and captures git errors when outside a repo.
  - Unit tests: `uv run pytest tests/test_git_file_selection.py tests/test_error_handling.py`
    Expected: Git selection includes tracked + untracked-not-ignored files and returns UQF000/UQF001/UQF002/UQF003 deterministically.
    Rationale: Git behavior varies by environment and repo state, so isolated tests in temp repos are required to lock down the exact `git ls-files` semantics and error codes without relying on developer machines.
  - Doc tests: `src/uniqfunc/model.py` doctests pass and reflect the parsing behavior.

## Task 2: Parser extraction (`parser.py`)

  Goal: Extract all function defs (including nested and methods) with annotations and docstrings while preserving error reporting.

- [ ] 2.1 Implement `parser.py` to extract function defs (including nested/methods), parameters, return annotations, and docstrings, capturing UQF001 for syntax errors without aborting the scan.
- [ ] 2.2 Add function-level doctests covering simple defs, nested defs, and annotation parsing.
- [ ] 2.3 Write `tests/test_parser.py` to validate extraction order, syntax error handling, and deterministic output fields.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format json`
    Expected: Reports UQF001 for a syntax error file while still emitting valid JSON for the rest of the repo.
  - Unit tests: `uv run pytest tests/test_parser.py`
    Expected: Functions, parameters, return annotations, and docstrings are extracted consistently for nested, method, and async defs.
    Rationale: AST parsing rules are easy to regress during refactors, and errors must not abort the scan. Unit tests pin down these edge cases and ensure ordering and fields remain deterministic.
  - Doc tests: `src/uniqfunc/parser.py` doctests pass and serve as the primary executable examples.

## Task 3: Fingerprinting (`fingerprint.py`)

  Goal: Produce a deterministic canonical token stream and shingled representation for AST similarity scoring.

- [ ] 3.1 Implement `fingerprint.py` canonical token stream normalization and shingling (5-grams) with deterministic ordering.
- [ ] 3.2 Add function-level doctests that demonstrate identifier normalization and constant bucketing.
- [ ] 3.3 Write `tests/test_fingerprint.py` to validate token normalization, shingle generation, and stability across runs.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.fingerprint -h`
    Expected: Shows usage text for the module entry point and exits 0.
  - Unit tests: `uv run pytest tests/test_fingerprint.py`
    Expected: Fingerprints normalize identifiers and constants consistently and produce stable shingles for representative code snippets.
    Rationale: Fingerprints drive similarity scoring and must be stable across runs and platforms. Unit tests guard the normalization rules against subtle changes that would otherwise alter candidate rankings.
  - Doc tests: `src/uniqfunc/fingerprint.py` doctests pass and illustrate the token stream behavior.

## Task 4: Similarity scoring (per-strategy modules)

  Goal: Rank reuse candidates with deterministic scores by implementing name/signature and AST fingerprint strategies in separate modules, then combining them.

- [ ] 4.1 Implement `similarity_name_signature.py` for snake_case token overlap, edit similarity, param-count similarity, param-name overlap, and return annotation matching.
- [ ] 4.2 Implement `similarity_ast.py` to compute AST similarity from fingerprint shingles (Jaccard or token multiset overlap).
- [ ] 4.3 Implement `similarity.py` to combine per-strategy scores with weights and rank top-k candidates deterministically, honoring a caller-provided threshold.
- [ ] 4.4 Add function-level doctests for per-strategy helpers and the combined scorer.
- [ ] 4.5 Write `tests/test_similarity.py` to validate thresholds, top-k behavior, and negative cases across both strategies.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.similarity_name_signature -h`
    Expected: Shows module usage for the name/signature strategy and exits 0.
  - CLI: `uv run --env-file .env -m uniqfunc.similarity_ast -h`
    Expected: Shows module usage for the AST strategy and exits 0.
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format json`
    Expected: Includes `reuse_suggestions` for intentionally similar functions and excludes dissimilar pairs at the default threshold.
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format json --similarity-threshold 0.95`
    Expected: Emits fewer or no suggestions for the same input due to the higher threshold.
  - Unit tests: `uv run pytest tests/test_similarity.py`
    Expected: Candidates are ordered deterministically, scores meet threshold rules (including custom thresholds), and top-5 truncation is enforced.
    Rationale: Small changes in scoring weights or tokenization can silently change suggestions. Unit tests lock the ranking behavior and thresholds so agent workflows stay predictable.
  - Doc tests: `src/uniqfunc/similarity_name_signature.py` doctests pass, `src/uniqfunc/similarity_ast.py` doctests pass, and `src/uniqfunc/similarity.py` doctests pass.

## Task 5: Duplicate detection and output formatting

  Goal: Produce deterministic diagnostics and exit codes for both text and JSON modes.

- [ ] 5.1 Implement duplicate detection across all functions with deterministic sorting by `(path, line, name)`.
- [ ] 5.2 Implement `formatters.py` for text output (UQF100/UQF200/UQF201) and JSON output schema.
- [ ] 5.3 Implement `cli.py` with argparse, `--format` and `--similarity-threshold` flags, exit code logic, and routing of stdout/stderr.
- [ ] 5.4 Add `__main__` blocks to each module with DEBUG logging and example usages in docstrings.
- [ ] 5.5 Write `tests/test_cli_text_output.py` and `tests/test_cli_json_output.py` to assert stable formatting and ordering.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format text`
    Expected: VS Code-clickable diagnostics with correct codes, stable ordering, and exit code 1 on duplicates.
  - Unit tests: `uv run pytest tests/test_cli_text_output.py tests/test_cli_json_output.py`
    Expected: Text lines are VS Code-clickable and JSON output is stable and schema-correct across runs.
    Rationale: Output format is a contract with editors and agents. Unit tests catch formatting regressions and ordering drift that would be painful to detect manually.
  - Doc tests: `src/uniqfunc/cli.py` doctests pass and match usage examples.

## Task 6: Packaging and documentation

  Goal: Align project metadata, README, and tooling with the SPEC.

- [ ] 6.1 Update `pyproject.toml` to Hatchling metadata, version, scripts, dependencies, and pytest config per SPEC.
- [ ] 6.2 Update `Makefile` targets for lint/test using the new package layout.
- [ ] 6.3 Create `README.md` with required sections, examples, and output snippets.
- [ ] 6.4 Regenerate `CONTEXT.md` after public API/module layout is finalized.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --version`
    Expected: Prints `0.1.0` and exits 0.
  - Unit tests: `uv run pytest`
    Expected: All tests pass with deterministic output ordering.
    Rationale: Packaging and docs changes are easy to ship without noticing behavioral regressions. Running the full unit suite ensures the CLI contract and output formats still match SPEC before release.
  - Doc tests: `src/uniqfunc/cli.py` doctests pass and remain consistent with README examples.
