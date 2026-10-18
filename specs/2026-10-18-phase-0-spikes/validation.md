# Phase 0: Spikes. Validation

Done only when every box is checked with a test name or evidence note. Expected discovery of an unsupported stock API is a recorded experimental result; it does not waive the required working OpenUI route, packaged sidecar cleanup, demo run, or containment checks.

## Automated
- [ ] R1: dependency locks resolve; recorded environment and exact versions match installed packages; executable spike files remain under `spikes/`.
- [ ] Quality: ruff, strict mypy over all Python spike modules, pytest, and `tsc --noEmit` over both renderer and Electron code pass. Record exact working directories, commands, and totals; the Phase 0 equivalent of the future `backend` gate is explicit.
- [ ] R2: tests render `Callout`, `Stack`, and `KeyValue` from OpenUI Lang using the installed libraries; prompt generation includes the component definitions.
- [ ] R2: Electron tests run a static export under both `file://` and `app://`, record assets/renderer failures per protocol, and demonstrate at least one fully working route.
- [ ] R2: controlled chunk delivery produces intermediate and final rendered output; malformed input shows readable fallback without an uncaught error.
- [ ] R3: packaged sidecar's first stdout line parses as the port announcement; the bound socket is loopback-only; correct/absent/wrong bearer token yields 200/401/401.
- [ ] R3: repeated launches use fresh ephemeral tokens and OS-assigned ports without a probe-then-bind race; launch failure cleans up spawned processes.
- [ ] R4: normal Electron quit removes the packaged engine and its fixture descendant within 5 seconds.
- [ ] R4: force-killing Electron main removes the packaged engine and its fixture descendant within 5 seconds; this test does not kill the tree itself before asserting cleanup.
- [ ] R3/R10: generated canary secrets and tokens are absent from captured stdout/stderr, process command lines, and experiment-produced artifacts. Test output itself never prints the canary.
- [ ] R5: actual `create_deep_agent` parameter wiring is exercised and captured model messages prove replacement of the default system prompt.
- [ ] R5: real agent calls exercise `write_todos` and `task`; tests identify their activity in captured stream envelopes.
- [ ] R5: an interrupt pauses a run and a verified decision payload resumes it using in-memory checkpointing; approval and rejection paths are exercised.
- [ ] R6: stock backend tests cover PowerShell and cmd output, nonzero exit, timeout, and descendants. Test outcomes explicitly expose unsupported behavior rather than hiding it with skips; any leaked fixture process is cleaned up after observation.
- [ ] R7: an offline demo model streams text, emits a bound tool call, consumes its result, and finishes through `create_deep_agent`; network attempts cause the test to fail.
- [ ] R8: mocked provider adapter tests cover streamed/non-streamed DeepSeek reasoning and Anthropic thinking, preserved field paths or verified absence, ordinary text separation, and missing reasoning.
- [ ] R9: temporary Windows path tests allow an internal file and block traversal, absolute outside paths, sibling-prefix collisions, drive-relative and UNC inputs, with case/separator variants.
- [ ] R9: real symlink and junction fixtures block outside targets, including a new file beneath an escaping linked parent. No privilege-dependent case is counted as passing when skipped.

## Manual (Windows 10/11)
- [ ] R2: open the working static-export protocol in Electron; observe progressive cards, nested stack/key-value content, and readable malformed-input fallback. Capture evidence without secrets. There are no product screens to compare against the mock in Phase 0.
- [ ] R3/R4: launch the packaged sidecar from Electron on Windows; independently inspect bind address and process IDs, then verify normal quit and force-kill leave no engine or descendant behind.
- [ ] R6: inspect PowerShell/cmd timeout and descendant results; document whether the stock backend is suitable or requires a custom command tool.
- [ ] R9: run link fixtures with sufficient Windows privileges; inspect cleanup and document the containment candidate's race/alias limitations.
- [ ] R10: review `learnings.md` for exact versions, official/installed-source references, signatures, runnable snippets, recorded failures and workarounds, and explicit supported/unsupported/unresolved outcomes.
- [ ] R10: every TODO/unresolved result has an impact and next action; Phase 1 receives a protocol recommendation, sidecar lifetime mechanism, demo-model pattern, deepagents API/stream/interrupt notes, reasoning mapping, and jail findings.
- [ ] R10: any constitution amendments have explicit user approval before being applied; the roadmap accurately records completion after all validation passes. If no amendments are necessary, record that conclusion.

## Exit criteria
All checks above have evidence, `learnings.md` exists in this dated phase folder, required constitution updates are approved and committed, and each implementation plan step has its own commit. No product code has been introduced.
