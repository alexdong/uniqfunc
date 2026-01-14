# uniqfunc

A git-aware checker for AI-generated Python code that enforces repo-wide unique function names (blocking) and emits reuse candidates for agent review (non-blocking).

## Recommended agent loop (Codex)

1. Generate or modify code.
2. Run `uvx uniqfunc --format json`.
3. If exit code `1`, fix naming conflicts until clean.
4. If `reuse_suggestions` are present, consider reusing or refactoring existing functions.

## VS Code integration

Text output is VS Code-clickable because every diagnostic line begins with `path:line:col` (no leading spaces).

## Usage

```bash
uvx uniqfunc
```

Defaults ignore `main` and `cli`. Add more exclude patterns (repeatable regex):

```bash
uvx uniqfunc --exclude-name '^main$' --exclude-name '^cli$'
```

## Output examples

Text (duplicate):

```text
path/to/file.py:10:1 UQF100 duplicate function name 'foo' (also in other.py:42:1) signature=def foo(): also_signature=def foo():
```

Text (reuse suggestions):

```text
=== UNIQFUNC LLM REUSE SUGGESTIONS ===
src/timeutils.py:12:1 UQF200 reuse_candidate target=epoch_to_aware_datetime candidates=1 signature=def epoch_to_aware_datetime(epoch_seconds) -> datetime:
src/timeutils.py:5:1 UQF201 candidate_for=epoch_to_aware_datetime target_loc=src/timeutils.py:12:1 name=epoch_to_datetime score=0.83 signals=name_token_jaccard:0.66 signature:0.75 ast:0.90 signature=def epoch_to_datetime(epoch) -> datetime:
=== END UNIQFUNC LLM REUSE SUGGESTIONS ===
```

JSON:

```json
{
  "version": "0.1.3",
  "repo_root": "/abs/path",
  "naming_conflicts": [
    {
      "code": "UQF100",
      "name": "foo",
      "occurrence": {"path": "a.py", "line": 10, "col": 1},
      "first_seen": {"path": "b.py", "line": 42, "col": 1}
    }
  ],
  "reuse_suggestions": [
    {
      "target": {"path": "timeutils.py", "line": 12, "col": 1, "name": "epoch_to_aware_datetime"},
      "candidates": [
        {
          "path": "timeutils.py",
          "line": 5,
          "col": 1,
          "name": "epoch_to_datetime",
          "score": 0.83,
          "signals": {
            "name_token_jaccard": 0.66,
            "signature_score": 0.75,
            "ast_score": 0.90
          }
        }
      ]
    }
  ],
  "errors": []
}
```

## Notes

- Requires a git repo and uses `git ls-files` for file selection.
- No config by design.
