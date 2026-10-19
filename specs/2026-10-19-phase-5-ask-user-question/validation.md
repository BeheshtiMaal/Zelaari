# Phase 5: AskUserQuestion GenUI. Validation

Status: **Draft; no checks executed for Phase 5.** Done only when every box has passing evidence. Add actual test names/commands/artifact references as work completes.

## Automated
- [ ] R1–R2: schema tests cover 1/3 and invalid 0/4 questions, 2/4 and invalid option counts, empty/duplicate IDs, bounded strings, types, descriptions and Other availability.
- [ ] R2: single option/Other, multi selections/Other/both, complete reordered rank/optional Other and declined result round-trip as structured tool results; duplicate/unknown/missing IDs and blank selected Other are rejected.
- [ ] R3: real graph emits question-only, approval-only and mixed barriers; safe/approved sibling tools do not execute until all required calls have answers. Test reverse decision order, multiple question calls, partial answers, rejected approvals and independent returned results.
- [ ] R3: Read-only/Ask/Auto questions render without a redundant approval; question answers never authorize denied or pending tools. Existing jail, rules, revisions, snapshots and uncertain-effect no-replay tests remain green.
- [ ] R4: no/wrong-token routes fail; correct-token retrieval/answer succeeds. Cross-run/graph/call IDs, malformed answers, duplicate answers, stopped runs and historical controls cannot resume work. Old approval API/configuration clients remain compatible.
- [ ] R5: real SQLite saver/graph reconstruction restores pending question and mixed requests with exact identities; partial answers survive and complete only once; event replay remains monotonic without duplicate publication.
- [ ] R5: actual engine force-kill mid-question and after one mixed answer preserves original run and decisions; graceful quit preserves, explicit Stop cancels. Missing key/provider identity/workspace retain actionable pending state; restored dependencies permit continuation.
- [ ] R6: QuestionCard exists in generated OpenUI library/prompt; deterministic and OpenUI references share the real component. Forged/unknown/cross-run references expose no live controls. Malformed GenUI retains readable fallback.
- [ ] R7–R8: UI tests cover radios, checkboxes, ranking via pointer and keyboard, Other, back/next draft retention, incomplete submit refusal, decline, resolved history, immediate locking and failure recovery.
- [ ] R8: keyboard tests cover digits 1–4, dynamic hints, Enter navigation/submission, Esc decline, focus/ARIA and ordering announcements. Editable text/IME/composer/picker events cannot accidentally answer or decline. Logical CSS check passes.
- [ ] R9: question-only task has amber dot and zero approval badge; mixed task summary counts request batches plus approvals. Resolve either kind first, switch tasks/workspaces, replay and restart without clearing remaining waits or putting questions in the inbox.
- [ ] R10: `/grill` parses only as a leading command; persisted interview starts with real questions, supports at least two successive batches, carries answers forward and restores mid-interview. Premature mutation/command attempts are refused; readiness requires an answered batch and structured summary, then original-task actions use ordinary permissions. Decline/Stop starts no implementation.
- [ ] R11: command picker filter, arrow/Enter/Esc, pointer selection and Home chip work; selection inserts editable `/grill` without submitting. Unknown slash/plain text is preserved; keyboard scope is isolated.
- [ ] R12: exhausted consumer uses actual supplied failure context and stable three-choice results; retry carries hint, change approach returns its intent, stop/report terminates fixture safely and keeps approved changes. No automatic Phase 7 budgets are claimed.
- [ ] R13: canary credentials in question content/options, Other/hints and model/tool results never enter event files, question records, checkpoints, logs or generated fixture artifacts; no vault secret stored in workspace.
- [ ] R14: `uv run --project backend ruff check backend`, `uv run --project backend mypy --strict backend`, `uv run --project backend pytest backend/tests` pass, including Phase 4 regressions.
- [ ] R14: `npm run typecheck`, `npm run test:ui`, `npm run generate:protocol`, `npm run generate:genui`, `npm run build`, `npm run build:electron` and `npm run test:desktop` pass; generated artifacts are reproducible and diff checks clean.

## Manual / automated Windows Electron walkthroughs
Use actual engine/preload/auth/SQLite and disposable workspaces/profiles. Local offline provider fixtures and built-in Demo require no external key. Store generated screenshots/evidence in `artifacts/phase5/`, without committing secrets or runtime data.

- [ ] Main docked card matches mock at 1440×900 in Persian: real chip/index/title/options/descriptions/Other/footer, teal selected states, proper placement above composer. Capture and inspect English mirror and a narrow viewport without clipped controls.
- [ ] Complete single, multi and rank requests, including all-Other answers where valid, pointer/keyboard reorder, three-question navigation and final structured continuation. Inspect selected defaults without treating them as answers.
- [ ] Enter/Esc and digits work within the focused card; text editing, Persian IME, composer and slash picker do not activate those decisions. Visible focus and screen-reader semantics are verified.
- [ ] Dismiss a question; model receives declined, run continues safely, history remains readable and controls inactive. A failed network submission preserves the draft and can be retried once.
- [ ] Keep a question and file approval pending in one task, plus a question in another workspace. Verify inline-only questions, per-task dots/summary, approval-only inbox badge and independent resolution in either order.
- [ ] Force-kill the engine during a pending mixed request, reopen, resolve remaining original questions/approvals and verify one effect only. Repeat graceful quit, partial decision, missing key/workspace restoration and explicit Stop.
- [ ] Type `/`, filter/select `/grill` with keyboard and pointer; use Home interview chip. Run a multi-batch interview, restart mid-interview, inspect readiness summary and approve actual implementation only afterward. Declining an interview performs no implementation.
- [ ] Render exhausted-attempts variant from real fixture data; inspect Errors mock labels/context/output, submit retry with hint and change approach, then stop/report on a separate run while prior approved changes remain. Record automatic exhaustion production as Phase 7.
- [ ] Recheck existing Demo read/edit, approval/edit/reject, Rules always-ask, branch/worktree and Undo behavior; no renderer errors, auth regressions or orphan processes after normal/forced close.

## Exit criteria
- [ ] Every requirement R1–R14 has passing evidence above; no unsupported completion claim or unresolved spec/mock conflict.
- [ ] `learnings.md` records verified installed APIs, readiness transition, durable ordering, accessibility choices, scope limits and Phase 6/7/8 handoff; no new unresolved TODO without an entry.
- [ ] Exact roadmap completion row/handoff explicitly approved, applied and committed with final phase changes; each earlier plan step has its own commit. Later phases retain their names/order.
