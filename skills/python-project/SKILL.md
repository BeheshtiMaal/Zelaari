---
name: python-project
description: Structure, typing, pytest and ruff conventions for a Python project.
category: coding
---
# Python project

Use this when a task touches a Python codebase and the conventions are not obvious from
the repository. Read the existing `pyproject.toml` first; it wins over this file.

## Layout

- `src/<package>/` for importable code, `tests/` mirroring it by module name.
- One concern per module. A module that needs a table of contents is two modules.
- No import-time side effects: no network, no filesystem writes, no engine construction.
  A module must be importable in a test with no arguments.

## Typing

- Annotate every public function; `mypy --strict` is the target, not a suggestion.
- Prefer `str | None` over `Optional[str]`, `list[str]` over `List[str]`.
- Use Pydantic models at boundaries (HTTP, files, tool arguments) and plain dataclasses
  inside. Validate once, then trust the value.
- Never silence a type error with `# type: ignore` without a comment that says which
  invariant makes it safe.

## Tests

- `pytest`, one behaviour per test, the name says the behaviour.
- Test the pure function directly; test the route with the real app and a temporary
  directory; test the screen in the desktop suite.
- A test that cannot fail is not a test: assert the value, not that the call returned.

## Style

- `ruff` with the repository's configuration; fix the cause, not the rule.
- Small functions, early returns, no deep nesting.
- Raise specific exceptions with a message a person can act on; never `except: pass`.
- Bound every loop over external input: file size, entry count, response size, timeout.

## Commands

```text
ruff check backend
mypy --strict backend
pytest backend/tests
```

Run them before you say the work is done, and quote the result.
