# Review prompt (run after each phase, ideally in a fresh session)

Act as a strict reviewer, not the author. Phase under review: **<PHASE NUMBER AND NAME>**.

1. Read `AGENTS.md`, the constitution, the phase folder (`requirements.md`, `plan.md`, `validation.md`, `learnings.md`) and `docs/design-tokens.md`.
2. Run all quality gates (`ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, plus phase checks) and report the real output.
3. Verify each `validation.md` box independently: re-run or re-read the evidence; mark any box you cannot confirm. Do not trust `learnings.md` claims without checking.
4. Compare every screen of this phase to its file in `docs/mock-source/`: layout, copy (exact Persian strings), tokens, RTL, states. List differences with file and line.
5. Security pass: jail escapes, permission bypasses, secrets in logs or events, unsafe defaults, anything the model could do without an approval that the spec says needs one.
6. Output: a table of findings (severity, file, issue, suggested fix) and a verdict: **accept**, **accept with fixes**, or **reject**. Do not fix anything yourself; propose fixes only.
