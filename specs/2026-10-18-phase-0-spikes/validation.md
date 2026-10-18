# Phase 0: Spikes. Validation

Done only when every box is checked with a test name or evidence note. Expected discovery of an unsupported stock API is a recorded experimental result; it does not waive the required working OpenUI route, packaged sidecar cleanup, demo run, or containment checks.

## Automated
- [x] R1: dependency locks resolve; recorded environment and exact versions match installed packages; executable spike files remain under `spikes/`. Evidence: `test_locked_environment`, uv sync/locks, Git source review.
- [ ] Quality: ruff, strict mypy over all Python spike modules, pytest, and `tsc --noEmit` over both renderer and Electron code pass. Record exact working directories, commands, and totals; the Phase 0 equivalent of the future `backend` gate is explicit.
- [x] R2: tests render `Callout`, `Stack`, and `KeyValue` from OpenUI Lang using the installed libraries; prompt generation includes the component definitions. Evidence: `ui/tests/electron.ts`, both protocols.
- [x] R2: Electron tests run a static export under both `file://` and `app://`, record assets/renderer failures per protocol, and demonstrate at least one fully working route. Evidence: `openui.json`, CSS/request-failure assertions.
- [x] R2: controlled chunk delivery produces intermediate and final rendered output; malformed input shows readable fallback without an uncaught error. Evidence: hydrated, settled-render assertions and screenshots.
- [x] R3: packaged sidecar's first stdout line parses as the port announcement; the bound socket is loopback-only; correct/absent/wrong bearer token yields 200/401/401. Evidence: `test_packaged_electron_lifetime` and launcher first-line validation.
- [x] R3: repeated launches use fresh ephemeral tokens and OS-assigned ports without a probe-then-bind race; launch failure cleans up spawned processes. Evidence: both lifecycle cases, `SEEN_TOKENS`, bound socket reuse, `test_watchdog_start_failure`.
- [x] R4: normal Electron quit removes the packaged engine and its fixture descendant within 5 seconds. Evidence: `test_packaged_electron_lifetime[False]`, `sidecar-normal.json`.
- [x] R4: force-killing Electron main removes the packaged engine and its fixture descendant within 5 seconds; this test does not kill the tree itself before asserting cleanup. Evidence: `test_packaged_electron_lifetime[True]`, `sidecar-force.json`.
- [x] R3/R10: generated canary secrets and tokens are absent from captured stdout/stderr, process command lines, and experiment-produced artifacts. Test output itself never prints the canary. Evidence: lifecycle fixture leakage checks, environment checks, artifact scan.
- [x] R5: actual `create_deep_agent` parameter wiring is exercised and captured model messages prove replacement of the default system prompt. Evidence: `test_api_activity_and_demo`.
- [x] R5: real agent calls exercise `write_todos` and `task`; tests identify their activity in captured stream envelopes. Evidence: `test_api_activity_and_demo`, `agent-stream.json`; explicit todo middleware required.
- [x] R5: an interrupt pauses a run and a verified decision payload resumes it using in-memory checkpointing; approval and rejection paths are exercised. Evidence: both `test_interrupt_resume` cases and captured payloads.
- [x] R6: stock backend tests cover PowerShell and cmd output, nonzero exit, timeout, and descendants. Test outcomes explicitly expose unsupported behavior rather than hiding it with skips; any leaked fixture process is cleaned up after observation. Evidence: both `test_stock_windows_shell` cases; stock safety is unsupported.
- [x] R7: an offline demo model streams text, emits a bound tool call, consumes its result, and finishes through `create_deep_agent`; network attempts cause the test to fail. Evidence: `test_api_activity_and_demo` socket guard.
- [x] R8: mocked provider adapter tests cover streamed/non-streamed DeepSeek reasoning and Anthropic thinking, preserved field paths or verified absence, ordinary text separation, and missing reasoning. Evidence: six `test_reasoning.py` cases.
- [x] R9: temporary Windows path tests allow an internal file and block traversal, absolute outside paths, sibling-prefix collisions, drive-relative and UNC inputs, with case/separator variants. Evidence: eight passing containment cases, including junction.
- [ ] R9: real symlink and junction fixtures block outside targets, including a new file beneath an escaping linked parent. No privilege-dependent case is counted as passing when skipped.

## Manual (Windows 10/11)
- [x] R2: open the working static-export protocol in Electron; observe progressive cards, nested stack/key-value content, and readable malformed-input fallback. Capture evidence without secrets. There are no product screens to compare against the mock in Phase 0. Evidence: Windows Electron runs, DOM observations, inspected final/fallback screenshots.
- [x] R3/R4: launch the packaged sidecar from Electron on Windows; independently inspect bind address and process IDs, then verify normal quit and force-kill leave no engine or descendant behind. Evidence: reviewed OS process/socket observations in both sidecar JSON files; no owned Electron processes remained.
- [x] R6: inspect PowerShell/cmd timeout and descendant results; document whether the stock backend is suitable or requires a custom command tool. Evidence: reviewed both shell JSON files and installed implementation; custom tool required.
- [ ] R9: run link fixtures with sufficient Windows privileges; inspect cleanup and document the containment candidate's race/alias limitations.
- [x] R10: review `learnings.md` for exact versions, official/installed-source references, signatures, runnable snippets, recorded failures and workarounds, and explicit supported/unsupported/unresolved outcomes. Evidence: learnings and source/example review.
- [x] R10: every TODO/unresolved result has an impact and next action; Phase 1 receives a protocol recommendation, sidecar lifetime mechanism, demo-model pattern, deepagents API/stream/interrupt notes, reasoning mapping, and jail findings. Evidence: learnings handoff and concrete amendment proposal.
- [ ] R10: any constitution amendments have explicit user approval before being applied; the roadmap accurately records completion after all validation passes. If no amendments are necessary, record that conclusion.

## Exit criteria

Current status: **pending**, not complete. Full pytest: 24 passed, 1 failed (symlink creation, Windows error 1314). Ruff, strict mypy (11 files), tsc, static export, and both Electron protocol tests pass. Enable symlink creation and rerun the real test. Constitution amendments are proposed separately and await approval; the roadmap is unchanged. These outstanding checks are intentionally unticked.
All checks above have evidence, `learnings.md` exists in this dated phase folder, required constitution updates are approved and committed, and each implementation plan step has its own commit. No product code has been introduced.
