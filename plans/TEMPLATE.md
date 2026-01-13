---
name: <plan-slug>
description: <short, specific description of the work>
One-shot reference: `plans/completed/benchmark.md`
---

# Plan

<1-3 paragraph summary of the goal, constraints, and the high-level approach.>

## Requirements

- <bullet requirement>

## Scope

- In: <what is included>
- Out: <what is excluded>
- Assumptions: <key assumptions and dependencies>

## Files and entry points

- `<path>`: <what changes or exists here>

  Usage docstring (when needed):

  ```python
  """One-line purpose.

  Usage:
      uv run --env-file .env -m <module> -h
      uv run --env-file .env -m <module> <example>
  """
  ```

  Public functions (include doctests immediately after the signature):

  ```python
  def example(value: int) -> int:
      """One-line purpose.

      Examples:
          >>> example(2)
          4
      """
  ```

## Data model / API changes

- <new or updated models, fields, or endpoints>

## Action items

  [ ] 1. <short action>
  [ ] 2. <short action>

## Task 1: <task name>

  Goal: <short statement of intent>

- [ ] 1.1 <step>
- [ ] 1.2 <step>

  Acceptance criteria:
  - CLI: `<command>`
    Expected: <explicit output or behavior>
  - Doc tests: <module or function> doctests pass and reflect acceptance behavior.

## Task 2: <task name>

  Goal: <short statement of intent>

- [ ] 2.1 <step>
- [ ] 2.2 <step>

  Acceptance criteria:
  - CLI: `<command>`
    Expected: <explicit output or behavior>
  - Doc tests: <module or function> doctests pass and reflect acceptance behavior.
