---
name: fix-failing-tests
description: Run the tests, read the first failure, fix it, and repeat until green.
command: /fix
category: tests
---
# Fix failing tests

Work from the failure, not from the file you suspect. The loop is small and it is the
whole skill.

## The loop

1. **Run the suite** with the project's verification command (the harness resolves it;
   `pytest -q` or `npm test` in most repositories). Never guess a command: if none is
   detected, ask.
2. **Read the first failure only.** The traceback, the assertion diff, the actual value.
   Later failures are often the same cause and will disappear with it.
3. **State one hypothesis** in a sentence before editing: "the parser returns a string
   but the caller compares a tuple". If you cannot state it, read more code — do not edit.
4. **Make the smallest change** that tests the hypothesis. One idea per attempt.
5. **Re-run the same command.** A fix that is not followed by the command is not a fix.
6. Repeat until green, or until the attempt budget is exhausted. Then report honestly:
   what fails, what you tried, what you believe the cause is.

## What not to do

- Do not weaken, skip, rename or delete a test to make it pass. A test that asserts the
  wrong thing is a finding to report, not a thing to silence.
- Do not catch the exception the test is about, and do not widen a type to `Any` to make
  the checker quiet.
- Do not run the whole suite with `-x` removed to "see everything" before the first fix;
  it multiplies output without adding information.
- Do not reformat unrelated files. The diff should explain the failure.

## Reporting

When the suite is green, say which command proved it and how many tests passed. If the
run ended with failures, name the failing test ids and the one hypothesis you would try
next.
