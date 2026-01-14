---
name: output-details-exclusions
description: Add signature details to text output and allow excluding function name patterns.
---

# Plan

We need richer text output so each duplicate or reuse suggestion shows function signatures, and we need a way to exclude function-name patterns such as `main` or `cli` from both conflict detection and reuse suggestions. The approach is to extend scanning with optional name-pattern filters, carry excluded-function metadata for reporting, and update text formatting to show signatures and target locations.

We will compute a readable signature string from the AST so it reflects annotations and defaults without altering similarity scoring. Text output will append `signature=` (and `target_loc=` for candidates) while preserving VS Code clickability. Tests will be updated to assert the new details, and documentation will be updated to describe the new flag and output fields.

## Requirements

- Text output shows function signature for duplicates and reuse suggestions.
- Reuse candidate lines include target location for quick triage.
- CLI supports repeatable `--exclude-name` regex patterns.
- Excluded functions are removed from both conflicts and suggestions.
- JSON schema remains unchanged.

## Scope

- In: signature capture in parser, text formatter updates, CLI filtering, tests, docs.
- Out: JSON schema changes, configuration files, dependency changes.
- Assumptions: regex patterns are provided by users and should be validated by argparse.

## Files and entry points

- `src/uniqfunc/model.py`: extend `FuncRef` and `ScanResult` data to support signatures and exclusions.
- `src/uniqfunc/parser.py`: build readable signature strings from AST nodes.
- `src/uniqfunc/cli.py`: compile and apply exclude-name patterns; pass metadata into `ScanResult`.
- `src/uniqfunc/formatters.py`: include signatures and target locations in text output.
- `tests/test_cli_text_output.py`: update expectations, add exclude-name tests.
- `README.md`, `SPEC.md`: document new text output fields and CLI flag.

## Data model / API changes

- `FuncRef.signature: str` added for output.
- `ScanResult.excluded_functions: list[FuncRef]` and `ScanResult.exclude_patterns: list[str]` added for reporting.
- `scan_repository(..., exclude_patterns=...)` signature updated.

## Action items

  [x] 1. Extend data models and parser to capture signatures.
  [x] 2. Add exclude-name pattern support in CLI scanning.
  [x] 3. Update text output formatting + tests.
  [x] 4. Update docs to reflect new behavior.

## Task 1: Capture signatures

  Goal: Provide readable function signatures for output without changing similarity scoring.

- [x] 1.1 Add `signature` to `FuncRef` and update constructors/doctests.
- [x] 1.2 Implement AST-based signature formatting in `parser.py`.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.parser path/to/file.py`
    Expected: parsed `FuncRef` includes a `signature` string with annotations and defaults.

## Task 2: Exclude-name patterns

  Goal: Allow users to ignore specified function name patterns.

- [x] 2.1 Add `--exclude-name` to CLI (repeatable regex) with validation.
- [x] 2.2 Filter functions before conflicts/suggestions and capture exclusions.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format text --exclude-name '^main$' .`
    Expected: no conflicts reported for functions named `main`.

## Task 3: Text output details + tests

  Goal: Add signature/target details to text output and update tests.

- [x] 3.1 Append `signature=` to UQF100/UQF200/UQF201 lines and add `target_loc=` to UQF201.
- [x] 3.2 Update text output tests and add exclude-name coverage.

  Acceptance criteria:
  - Pytest: `uv run --env-file .env -m pytest tests/test_cli_text_output.py -q`
    Expected: tests pass and output includes `signature=` fields.

## Task 4: Documentation

  Goal: Keep spec and README aligned with new output and flags.

- [x] 4.1 Update `SPEC.md` with new text fields and CLI flag.
- [x] 4.2 Update `README.md` output examples and usage/notes.

  Acceptance criteria:
  - Docs: `rg -n "exclude-name|signature=" SPEC.md README.md`
    Expected: docs mention the new flag and signature fields.
