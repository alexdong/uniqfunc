# Project Overview

Refer to `SPEC.md` for the purpose and function of this project.

## Tech Stack

- **Language & Packaging**: Python 3.12+ with stdlib-only runtime dependencies and strict type modeling via the standard library (`dataclasses`, `typing`). Project tooling managed by `uv` and standard `pyproject.toml` metadata. To run a module directly, use `uv run --env-file .env -m {module}` instead of `python -m {module}`.
- **Developer Tooling**: Makefile targets wrap `uv run` workflows; Ruff and Ty enforce linting and static analysis.
- **Interfaces & Observability**: CLI surfaces built with stdlib `argparse`; no external templating. Logging/diagnostics handled by stdlib `logging`.
- **Run Logs**: Each CLI run writes a timestamped log under `run/*.log`. When troubleshooting or validating behavior, prefer inspecting the latest log file and use `tail -f run/*.log` during long-running commands to pinpoint where a run stalls or fails.

## Development Principles

These opinionated principles contradict much of the common wisdom. Take the time to read and understand the philosophy behind them. Follow them religiously.

### Data Before Code

- Define types before writing code. Types are contracts between functions. They should be as tight as possible to avoid ambiguity. For example, prefer `list[str]` over `list`. Use stdlib data structures (`dataclasses`, precise `typing`) for complex models and keep runtime dependencies empty. Think of it as test-driven development for types. Refer to [`.claude/agents/datastructure.md`](.claude/agents/datastructure.md) for more details.
- `make lint` will run a new generation of formatters and type checkers, including `ruff`, `ty`, and `pyrefly`. Fix any issues before proceeding, even if the issues aren't in code you changed. If you disagree with a rule, discuss it with me and share your reasoning, but don't ignore or disable the rule.
- Leverage Python 3.12+ features for type annotations. Use algebraic data types for composite data types. Types are essentially concepts, so the fewer types we have, the better. Avoid deprecated constructs. Avoid `from __future__ import annotations`. We do not care about backward compatibility.

### Fail Early and Noisily

- Use `assert` statements liberally. Always include a detailed message. Make every function’s contract explicit and enforceable. Refrain from try/except blocks, union-with-None types (`| None`), or guarded early returns (`if ...: return`) unless necessary. Defensive programming is useful when interacting with external inputs, but once we are inside our code, we should aim to fail fast and loudly.
- Failing loudly makes the codebase easier to maintain in the long run by exposing internal flows and state transitions. Use stdlib `logging` to both document and observe the code's state.
- Add a `__main__` block at the end of each file in this project to provide a quick entry point to key features of the module for testing and debugging purposes. This applies only to uniqfunc's own code; treat scanned repositories as read-only. Make sure the log level is set to `DEBUG`. Use stdlib `argparse` to define and organize command-line interfaces when necessary. Always include example usages in the docstring. Make sure `uv run -m {module} -h` works and is mentioned in the docstring. Use stdlib `pprint` to pretty-print complex data structures and tables, but be conservative with its usage.
- Be mindful of the comments you leave behind. Unless they are absolutely necessary, drop them. If they can be replaced by `logging` messages, convert them. Remember that comments should explain the "why" behind complex logic, not the "what" or "how".
- When comments are warranted, write them as narratives rather than terse or bullet points. A reader should understand the options considered, trade-offs, reasoning, and context without needing to ask follow-up questions. Include urls, references and quick look-up tables when applicable.
- When you ship a bug fix or workaround, add detailed comment that states the observed error, the root cause (or best hypothesis), and why this fix is the chosen path.

### Shorter Code is Better Code

- After you've made code changes and both `make lint` pass, don't stop there. Instead, start rewriting the code until you can't further improve readability. Often the third or fourth iteration gives the best code.
- Put on a technical writer's hat and proofread code and log messages carefully. Apply Strunk & White principles to the code. Names should be well-thought-out and fit the problem domain like a glove. Use whitespace to group related code blocks together. Refer to [`.claude/agents/technicalwriter.md`](.claude/agents/technicalwriter.md) for more details.
- Functions should be short and focused but they also need to contain enough logic to warrant their existence. Always ask "will be code be easier to read if I inline this function?".
- Avoid defining classes or functions inside other functions. If a nested function captures variables from the enclosing scope, refactor to pass them as parameters instead.
- Avoid inline imports. Consolidate all imports at the top of the file.
- Do not introduce external configuration for this project. Avoid `pydantic-settings` and `.yaml` files; keep options explicit in code or CLI flags. If configuration becomes necessary, discuss it first and document the rationale.

### Optimise for Maintainability

- Defensive Programming and Backward Compatibility hurts more in the long run because they add cognitive load and visual noise. Always prefer the simplest solution that works for the current requirements.
- We do not care about backward compatibility. We can always reprocess data if needed. We prioritize code clarity and correctness over maintaining compatibility with old versions. Always prefer the simplest solution that works for the current requirements.
- When it comes to refactoring, prefer breaking changes over complex migration paths. Don't be afraid to delete old code. If you need to preserve history, we can always grep through git history.
- When it comes to dependencies, prefer the latest stable versions. Avoid using deprecated libraries or features. If a library is no longer maintained, find an alternative or consider writing the functionality ourselves.
- When it comes to type data structures, avoid deprecated constructs. Avoid `from __future__ import annotations`.
- Avoid `Optional` and `Union` types unless absolutely necessary. Avoid `TypedDict` unless you need to interoperate with untyped data (e.g., JSON).
- Avoid exceptions for control flow, unless absolutely necessary.

## Workflow

1. **Explore**: Spend time understanding the problem space, explore the codebase, and note down information that is relevant to the task at hand. Ask questions to clarify requirements and challenge assumptions.
2. **Plan**:
   - Start from `plans/TEMPLATE.md` and use `plans/completed/benchmark.md` as the one-shot reference for structure and detail.
   - Define data structures, function signatures, files/modules, and overall architecture.
   - Split work into tasks of similar size; each task is its own section with a clear goal.
   - Use `[ ]` for each step, and number both tasks and steps for easy reference.
   - Call out edge cases and error handling.
   - Save the plan as `plans/{plan-slug}.md` and include acceptance criteria as a CLI command, a doctest, or a pytest invocation.
   - When all steps are done, move the plan to `plans/completed/` (keep the filename).
   - This repo rule overrides any Codex plan skill storage guidance.
3. **Code**: Implement the code changes. Review and follow the plan file. Implement changes one task item at a time. Follow the "Development Principles". Ensure that both `make lint` and `make test` pass without issues before you move on to the next one. Check a TODO item off using `[x]` once it is done.
