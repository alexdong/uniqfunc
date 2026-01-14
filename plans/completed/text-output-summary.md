---
name: text-output-summary
description: Add a concise text-mode summary header to make CLI output more informative.
---

# Plan

The current text output only prints diagnostics, which makes it hard to confirm what was scanned or how big the result set is. I will add a short, deterministic summary header to text mode that reports the scan root, file count, function count, duplicate counts, suggestion counts, and error counts. This will stay non-diagnostic so VS Code clickability remains intact and JSON output remains unchanged.

The change requires capturing the scanned file list in the scan result, then formatting a summary header in `format_text`. I will cover the new header in tests so the behavior is locked in.

## Requirements

- Text output includes a brief summary header with scan root and counts.
- Diagnostic lines remain VS Code-clickable and unchanged.
- JSON output schema remains unchanged.

## Scope

- In: text output summary header, ScanResult carrying scanned files, tests for header.
- Out: JSON schema changes, suggestion block format changes, additional CLI flags.
- Assumptions: `list_python_files` returns a deterministic, sorted list.

## Files and entry points

- `src/uniqfunc/model.py`: extend `ScanResult` to store scanned files.
- `src/uniqfunc/cli.py`: populate `ScanResult.files` from git discovery.
- `src/uniqfunc/formatters.py`: emit text summary header using scan counts.
- `tests/test_cli_text_output.py`: assert summary header presence.

## Data model / API changes

- `ScanResult.files: list[Path]` added to preserve file list for reporting.

## Action items

  [x] 1. Capture scanned files in `ScanResult` and build summary counts.
  [x] 2. Emit a summary header in text output and add regression tests.

## Task 1: Capture scan metadata

  Goal: Store the scanned file list in the scan result to support summary output.

- [x] 1.1 Add `files` to `ScanResult` with a safe default.
- [x] 1.2 Populate `ScanResult.files` in `scan_repository`.

  Acceptance criteria:
  - CLI: `uv run --env-file .env -m uniqfunc.cli --format text .`
    Expected: header includes a `files=` count when run inside a git repo.

## Task 2: Text summary header

  Goal: Print a concise summary header before diagnostics in text output.

- [x] 2.1 Add summary formatting helpers in `formatters.py`.
- [x] 2.2 Update `format_text` to prepend the summary header.
- [x] 2.3 Add a test that asserts the header is present in text output.

  Acceptance criteria:
  - Pytest: `uv run --env-file .env -m pytest tests/test_cli_text_output.py -q`
    Expected: tests pass and text output includes the new summary header.
