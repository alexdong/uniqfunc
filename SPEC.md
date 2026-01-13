# uniqfunc — SPEC

## Purpose

**uniqfunc** is a small, fast, git-aware Python CLI tool that:

1) Detects **duplicate function names** across a repository (**blocking**)
2) Detects **potentially reusable / similar functions** and emits a **machine-friendly suggestion list** for an LLM/agent to review (**non-blocking**, informational)

It is intentionally designed to be:

- runnable via `uvx`
- deterministic and cheap
- dependency-free at runtime (stdlib-only)

### Primary audience

This tool is explicitly intended for **AI agents** (Codex / LLM codegen / autonomous refactoring bots) to enforce repository-wide rigor.

Recommended agent loop:

- Run uniqfunc after edits.
- If naming conflicts exist, fix until clean.
- If reuse suggestions exist, the agent reviews candidates and decides whether to reuse/refactor.

---

## Supported Python versions

- **Python >= 3.12 only**
- Use modern syntax freely (`|` unions, `list[str]`, etc.)

---

## What counts as a function

Included:

- `def name(...)`
- `async def name(...)`
- top-level functions, nested functions, and methods

Excluded:

- lambdas
- variables
- classes

Scoping is intentionally ignored: this is a repo-level naming discipline + reuse guardrail.

---

## File selection (git-aware)

uniqfunc MUST include:

- tracked files
- untracked files that are **not ignored**

Use exactly:

```bash
git ls-files -z --cached --others --exclude-standard -- '*.py'
````

This respects:

- `.gitignore`
- `.git/info/exclude`
- global git ignore rules

(No `--tracked-only` mode.)

---

## Checks

### Check 1: Global unique function names (blocking)

A naming conflict occurs when **two or more functions share the same name** in the scanned file set.

Included:

- `def foo(...)`
- `async def foo(...)`

Exit impact:

- If any naming conflicts are found, uniqfunc exits with **code 1**.

### Check 2: Similar function candidates (LLM review suggestions)

uniqfunc also emits a list of **candidate similar functions** intended for a downstream LLM/agent to review for potential reuse.

- This check is **non-blocking**.
- Deterministic and cheap.
- Produces:
  - the target function identity
  - top-k candidate existing functions with similarity scores
  - a short, structured rationale (name/signature similarity, AST fingerprint similarity)

The tool does **not** decide semantic equivalence; it only surfaces candidates.

#### Similarity strategy

Candidate retrieval is based on two deterministic signals:

Before diving in, two terms used below:

- **Shingles**: contiguous n-grams of the canonical token stream (e.g., 5 tokens at a time), used to capture local structure without full AST matching.
- **Jaccard similarity**: intersection size divided by union size for two shingle sets; higher values mean more shared structure.

1) **Name + signature similarity**
   - snake_case token overlap
   - normalized edit similarity on function name
   - parameter count + parameter-name overlap
   - return annotation string (if present)

   Example:

   - Target: `def epoch_to_aware_datetime(epoch_seconds: int) -> datetime`
   - Candidate: `def epoch_to_datetime(epoch: int) -> datetime`

   Name tokens:
   - `epoch_to_aware_datetime` -> `{"epoch", "to", "aware", "datetime"}`
   - `epoch_to_datetime` -> `{"epoch", "to", "datetime"}`
   - token overlap = 3/4 (Jaccard 0.75)

   Signature:
   - parameter count = 1 vs 1 (score 1.0)
   - parameter name overlap = `{"epoch_seconds"}` vs `{"epoch"}` (low overlap)
   - return annotation = `datetime` matches (score 1.0)

   The final name+signature score should reflect strong name overlap and identical return type even if parameter names are not identical.

2) **AST fingerprint similarity**
   - compute a lightweight canonical token stream from the function body
   - normalize local identifiers to placeholders
   - bucket constants (NUM/STR/NONE/BOOL)
   - retain operators and called function names
   - compute similarity via shingled n-gram Jaccard (default 5-grams) or token multiset overlap
   - fallback: if the canonical token stream is shorter than 5 tokens, skip shingling and use token multiset overlap to avoid unstable scores

   Example:

   - Target:

     ```python
     def clamp(x: int, lo: int, hi: int) -> int:
         if x < lo:
             return lo
         if x > hi:
             return hi
         return x
     ```

   - Candidate:

     ```python
     def clamp_value(value: int, minimum: int, maximum: int) -> int:
         if value < minimum:
             return minimum
         if value > maximum:
             return maximum
         return value
     ```

   Canonical token stream sketch (illustrative):
   - `IF`, `VAR`, `<`, `VAR`, `RETURN`, `VAR`, `IF`, `VAR`, `>`, `VAR`, `RETURN`, `VAR`, `RETURN`, `VAR`

   After shingling into 5-grams, the Jaccard similarity should be high because structure and operators are identical even though identifier names differ.

Final candidate score may be a weighted combination of the two.

#### Targets

To keep v0.1.0 minimal:

- treat **every function** as eligible for reuse suggestions (full scan)
- filter out self-matches
- return top 5 candidates per target above a threshold (default `>= 0.70`, configurable via CLI)

---

## CLI

### Invocation

```bash
uniqfunc [PATH]
````

- PATH defaults to `.`

### Flags

- `--format {text,json}` (default: `text`)
- `--similarity-threshold FLOAT` (default: `0.70`)
- `--version`
- `-h/--help`

---

## Output (VS Code-friendly)

### `--format text` (default)

**VS Code clickability requirement:** Every diagnostic line MUST start with:

`path/to/file.py:line:col`

- no leading spaces
- `line` is 1-based
- `col` is 1-based

This ensures VS Code terminal can click-through.

#### Naming conflicts

One line per naming conflict:

`path/to/file.py:line:col UQF100 duplicate function name 'foo' (also in other.py:line:col)`

#### Reuse suggestions (LLM review)

If similarity candidates exist, print a clearly delimited block:

```
=== UNIQFUNC LLM REUSE SUGGESTIONS ===
<one item per target function>
=== END UNIQFUNC LLM REUSE SUGGESTIONS ===
```

Within the block, each line MUST also be VS Code-clickable:

- Target summary line:

`path/to/target.py:line:col UQF200 reuse_candidate target=<funcname> candidates=<N>`

- Candidate lines (max 5 per target):

`path/to/candidate.py:line:col UQF201 candidate_for=<funcname> name=<candname> score=0.83 signals=name_token_jaccard:0.66 signature:0.75 ast:0.90`

### `--format json`

Emit a single JSON object to stdout:

```json
{
  "version": "0.1.0",
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
      "target": {"path": "new.py", "line": 12, "col": 1, "name": "epoch_to_aware_datetime"},
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
  "errors": [
    {"code": "UQF001", "path": "bad.py", "line": 1, "col": 1, "message": "syntax error: ..."}
  ]
}
```

JSON mode is intended for agent consumption.

---

## Diagnostic codes

| Code   | Meaning                                     |
| ------ | ------------------------------------------- |
| UQF000 | File could not be read                      |
| UQF001 | Syntax error in file                        |
| UQF002 | Git command failed / not a git repo         |
| UQF003 | Git executable not found                    |
| UQF100 | Duplicate function name                     |
| UQF200 | Reuse suggestion target summary (text mode) |
| UQF201 | Reuse suggestion candidate (text mode)      |

Routing:

- Naming conflicts + suggestions: stdout
- Operational errors: stderr

---

## Exit codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 0    | No naming conflicts (suggestions may still exist)  |
| 1    | Naming conflicts detected                          |
| 2    | Fatal error (git missing, not a repo, usage error) |

**Reuse suggestions do not change exit code** in v0.1.0.

---

## Repository layout

```bash
.
├── LICENSE
├── README.md
├── SPEC.md
├── pyproject.toml
├── src
│   └── uniqfunc
│       ├── __init__.py
│       └── cli.py
└── tests
    ├── test_cli_text_output.py
    ├── test_cli_json_output.py
    ├── test_git_file_selection.py
    └── test_similarity.py
```

---

## Implementation details

### Data model

Define a lightweight internal representation:

- `FuncRef(path: Path, line: int, col: int, name: str, params: list[str], returns: str | None, doc: str | None, ast_fingerprint: list[str])`

### Fingerprints

Implement `fingerprint_function(node) -> list[str]` producing canonical tokens:

- normalize local identifiers: `VAR`
- bucket constants: `NUM`, `STR`, `NONE`, `BOOL`
- keep operators and call target names (best-effort)
- produce a token list suitable for shingling

Compute:

- shingles (e.g., 5-grams) from tokens
- Jaccard similarity for AST score

### Similarity scoring

- `name_token_jaccard`: Jaccard of snake_case tokens
- `signature_score`: blend of:

  - param-count similarity
  - param-name overlap
  - return annotation match (if any)
- `ast_score`: Jaccard on fingerprint shingles
- `final_score`: weighted sum, e.g.:

  - 0.4 (name+signature)
  - 0.6 (ast)

Return:

- top 5 candidates per target
- only include candidates with `final_score >= 0.70`

Determinism:

- Sort functions and candidates by `(path, line, name)` before scoring/output
- Stable float formatting in text output (e.g., `0.83`)

---

## Packaging (PyPI)

### `pyproject.toml`

Use Hatchling.

Required:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "uniqfunc"
version = "0.1.0"
description = "Git-aware checker for globally unique Python function names + reuse suggestions for AI agents"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Alex Dong", email = "me@alexdong.com" }]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
uniqfunc = "uniqfunc.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/uniqfunc"]

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]
```

Runtime dependencies MUST remain empty.

---

## README.md requirements

README MUST highlight:

### What it is

- A mechanical validation tool for **AI-generated code**
- Enforces repo-wide unique function names (blocking)
- Emits “reuse candidates” for an LLM/agent to review (non-blocking)

### Recommended agent loop (Codex)

1. Generate or modify code
2. Run `uvx uniqfunc --format json`
3. If exit code `1`, fix naming conflicts until clean
4. If `reuse_suggestions` present, consider reusing/refactoring existing functions

### VS Code integration

- Text output is VS Code-clickable because every diagnostic line begins with `path:line:col` (no leading spaces).

### Usage examples

Keep this section minimal:

```bash
uvx uniqfunc
```

### Output examples

- Show UQF100 line
- Show suggestion block header and one UQF200/UQF201 example
- Show a short JSON example

### Notes

- Requires git repo
- Uses git to pick files
- No config by design

### README length guidance

- Keep the README as short as possible while still satisfying the required sections above.

---

## LICENSE

MIT license text.

---

## Manual acceptance tests

1. Duplicates -> exit 1, UQF100 printed
2. No duplicates -> exit 0
3. Syntax error -> UQF001 printed, scan continues
4. Outside git repo -> exit 2 with UQF002
5. `--format json` emits valid JSON even if errors exist
6. Similarity suggestions appear for obviously similar functions (e.g., copy/paste with minor edits)
7. Text output lines are VS Code-clickable (`path:line:col` prefix, no leading spaces)

---

## Testing requirements (pytest) — MUST be extensive

Unit tests MUST cover:

### Text output behavior

- UQF100 duplicate naming conflicts produce exact, VS Code-clickable lines
- Suggestion block presence/absence
- UQF200/UQF201 lines are also VS Code-clickable
- Stable ordering of output

### JSON output behavior

- Valid JSON emitted in all cases
- Fields present with correct types
- Stable ordering (sort by path+line+name) to keep diffs deterministic

### Git interaction

- Tests must not depend on machine git config.
- Use `tmp_path` to create a git repo during tests:

  - `git init`
  - create files
  - `git add` + commit for tracked files
  - create untracked files
  - create `.gitignore` and verify ignored files are excluded by `--exclude-standard`
- Assert file selection includes tracked + untracked-not-ignored.

### Similarity detection

- Construct two very similar functions and assert:

  - candidate appears in top-k
  - score is above threshold
- Construct dissimilar functions and assert no suggestion above threshold

### Error handling

- Syntax error file -> UQF001 captured, scan continues
- Unreadable file -> UQF000 captured
- Not a git repo -> exit 2 with UQF002
- Git not found -> exit 2 with UQF003

Tests should call `uniqfunc.cli:main` (or `run`) directly and capture stdout/stderr using pytest `capsys`.

---

## Notes for codex

- Generate exactly the files and behavior specified
- Do not add runtime dependencies
- Keep code explicit and readable
- Deterministic output
