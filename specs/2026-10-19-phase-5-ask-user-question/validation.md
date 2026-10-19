# Phase 5: AskUserQuestion GenUI. Validation

Status: **Phase 5 complete. Product validation passes; the user approved the exact roadmap update on 2026-10-19, applied and included with the final phase commit.**

## Automated
- [x] R1–R2: schema tests cover 1/3 and invalid 0/4 questions, 2/4 and invalid option counts, empty/duplicate IDs, bounded strings, types, descriptions and Other availability.
- [x] R2: single option/Other, multi selections/Other/both, complete reordered rank/optional Other and declined result round-trip as structured tool results; duplicate/unknown/missing IDs and blank selected Other are rejected.
- [x] R3: real graph emits question-only, approval-only and mixed barriers; safe/approved sibling tools do not execute until all required calls have answers. Test reverse decision order, multiple question calls, partial answers, rejected approvals and independent returned results.
- [x] R3: Read-only/Ask/Auto questions render without a redundant approval; question answers never authorize denied or pending tools. Existing jail, rules, revisions, snapshots and uncertain-effect no-replay tests remain green.
- [x] R4: no/wrong-token routes fail; correct-token retrieval/answer succeeds. Cross-run/graph/call IDs, malformed answers, duplicate answers, stopped runs and historical controls cannot resume work. Old approval API/configuration clients remain compatible.
- [x] R5: real SQLite saver/graph reconstruction restores pending question and mixed requests with exact identities; partial answers survive and complete only once; event replay remains monotonic without duplicate publication.
- [x] R5: actual engine force-kill mid-question and after one mixed answer preserves original run and decisions; graceful quit preserves, explicit Stop cancels. Missing key/provider identity/workspace retain actionable pending state; restored dependencies permit continuation.
- [x] R6: QuestionCard exists in generated OpenUI library/prompt; deterministic and OpenUI references share the real component. Forged/unknown/cross-run references expose no live controls. Malformed GenUI retains readable fallback.
- [x] R7–R8: UI tests cover radios, checkboxes, ranking via pointer and keyboard, Other, back/next draft retention, incomplete submit refusal, decline, resolved history, immediate locking and failure recovery.
- [x] R8: keyboard tests cover digits 1–4, dynamic hints, Enter navigation/submission, Esc decline, focus/ARIA and ordering announcements. Editable text/IME/composer/picker events cannot accidentally answer or decline. Logical CSS check passes.
- [x] R9: question-only task has amber dot and zero approval badge; mixed task summary counts request batches plus approvals. Resolve either kind first, switch tasks/workspaces, replay and restart without clearing remaining waits or putting questions in the inbox.
- [x] R10: `/grill` parses only as a leading command; persisted interview starts with real questions, supports at least two successive batches, carries answers forward and restores mid-interview. Premature mutation/command attempts are refused; readiness requires an answered batch and structured summary, then original-task actions use ordinary permissions. Decline/Stop starts no implementation.
- [x] R11: command picker filter, arrow/Enter/Esc, pointer selection and Home chip work; selection inserts editable `/grill` without submitting. Unknown slash/plain text is preserved; keyboard scope is isolated.
- [x] R12: exhausted consumer uses actual supplied failure context and stable three-choice results; retry carries hint, change approach returns its intent, stop/report terminates fixture safely and keeps approved changes. No automatic Phase 7 budgets are claimed.
- [x] R13: canary credentials in question content/options, Other/hints and model/tool results never enter event files, question records, checkpoints, logs or generated fixture artifacts; no vault secret stored in workspace.
- [x] R14: `uv run --project backend ruff check backend`, `uv run --project backend mypy --strict backend`, `uv run --project backend pytest backend/tests` pass, including Phase 4 regressions.
- [x] R14: `npm run typecheck`, `npm run test:ui`, `npm run generate:protocol`, `npm run generate:genui`, `npm run build`, `npm run build:electron` and `npm run test:desktop` pass; generated artifacts are reproducible and diff checks clean.

## Manual / automated Windows Electron walkthroughs
Use actual engine/preload/auth/SQLite and disposable workspaces/profiles. Local offline provider fixtures and built-in Demo require no external key. Store generated screenshots/evidence in `artifacts/phase5/`, without committing secrets or runtime data.

- [x] Main docked card matches mock at 1440×900 in Persian: real chip/index/title/options/descriptions/Other/footer, teal selected states, proper placement above composer. Capture and inspect English mirror and a narrow viewport without clipped controls.
- [x] Complete single, multi and rank requests, including all-Other answers where valid, pointer/keyboard reorder, three-question navigation and final structured continuation. Inspect selected defaults without treating them as answers.
- [x] Enter/Esc and digits work within the focused card; text editing, Persian IME, composer and slash picker do not activate those decisions. Visible focus and screen-reader semantics are verified.
- [x] Dismiss a question; model receives declined, run continues safely, history remains readable and controls inactive. A failed network submission preserves the draft and can be retried once.
- [x] Keep a question and file approval pending in one task, plus a question in another workspace. Verify inline-only questions, per-task dots/summary, approval-only inbox badge and independent resolution in either order.
- [x] Force-kill the engine during a pending mixed request, reopen, resolve remaining original questions/approvals and verify one effect only. Repeat graceful quit, partial decision, missing key/workspace restoration and explicit Stop.
- [x] Type `/`, filter/select `/grill` with keyboard and pointer; use Home interview chip. Run a multi-batch interview, restart mid-interview, inspect readiness summary and approve actual implementation only afterward. Declining an interview performs no implementation.
- [x] Render exhausted-attempts variant from real fixture data; inspect Errors mock labels/context/output, submit retry with hint and change approach, then stop/report on a separate run while prior approved changes remain. Record automatic exhaustion production as Phase 7.
- [x] Recheck existing Demo read/edit, approval/edit/reject, Rules always-ask, branch/worktree and Undo behavior; no renderer errors, auth regressions or orphan processes after normal/forced close.

## Exit criteria
- [x] Every requirement R1–R14 has passing evidence above; no unsupported completion claim or unresolved spec/mock conflict.
- [x] `learnings.md` records verified installed APIs, readiness transition, durable ordering, accessibility choices, scope limits and Phase 6/7/8 handoff; no new unresolved TODO without an entry.
- [x] Exact roadmap completion row/handoff explicitly approved by the user on 2026-10-19, applied and committed with final phase changes; each earlier plan step has its own commit. Later phases retain their names/order.

## Evidence index

| Requirements | Executed evidence |
|---|---|
| R1–R2 | `test_question_boundaries`, `test_option_and_answer_boundaries`, `test_answer_types`, `test_declined_and_wrong_identity`; UI selection/ranking tests in `tests/unit/questions.test.ts`. |
| R3–R5 | `test_mixed_barrier_sqlite_reconstruction`, `test_mixed_question_recovery[True/False]`, `test_two_question_calls_hold_all_sibling_tools`, `test_question_routes[ask/auto/read-only]`, `test_killed_question_engine_resumes_original_mixed_barrier`, `test_question_recovery_preserves_missing_dependencies`. |
| R4, R13 | Route tests also submit a question decision against a configuration approval and require 409 without a rules write. Wrong graph IDs, duplicate/incomplete answers and failed auth cannot dispatch. `test_question_privacy_and_stop` scans actual persistence, including question context/options/Other and SQLite; exhaustion integration scans retry-hint canaries. |
| R6–R8 | `tests/unit/question-controls.test.ts` refuses forged/unknown/cross-run OpenUI references; `tests/unit/questions.test.ts` validates selection, ordering and event replay. `tests/phase5-desktop.ts` checks complete batches, draft navigation, digits/Other, rank focus and keyboard move activation, pointer drag, Enter/Esc, text/IME safety, ARIA snapshot, immediate locking and failed network submission. |
| R9 | Existing inbox mixed-waiting unit plus real two-workspace desktop scenario: two amber task dots, approval-only badge, request-batch summary, independent question/approval resolution and reopening after kill. |
| R10 | `test_grill_restart_and_structured_ready`, `test_grill_prose_cannot_finish_without_readiness`, `test_grill_denies_premature_and_same_turn_effects`; the last also declines a later clarification after readiness and verifies normal implementation remains possible. Desktop drives two real batches and graceful restart before readiness. |
| R11 | `tests/unit/commands.test.ts`; desktop keyboard `/` selection, Escape dismissal and Home grill-me chip insert without submitting. |
| R12 | `test_exhausted_choices_return_hints_and_keep_approved_changes` first approves a real Demo edit, then verifies all three exhaustion outcomes, returned retry hints/redaction and unchanged approved file. Desktop submits each action through the actual QuestionCard. Automatic fix counters remain Phase 7. |
| R14 | Full Python gates, strict TypeScript, 37 UI tests, deterministic generation hashes, production/Electron builds, Phase 5 Electron walkthrough, baseline `test:desktop`, and `phase4-files-desktop.ts` branch/edit/byte-exact Undo/stale preview/Stop/worktree/Rules-always-ask/Rules-Undo regression. Final command counts are recorded below. |

Windows artifacts inspected at CSS 1440×900 and a narrow 800×800 viewport: `artifacts/phase5/question-fa.png`, `question-en.png`, `question-narrow-en.png`, `rank-en.png`, `exhausted-{Retry,Change,Stop}.png`; `evidence.json` records a passed real-engine walkthrough with no renderer errors. Dark layout, mirrored reading order, real 288px waiting panel, teal selection, failure badge/output, localized copy, visible focus and accessible ordering controls were inspected. Tall docks scroll instead of hiding controls. No external endpoint/key or remote CI claim is required.

## Final command results

- Ruff clean; strict mypy passes for **95 source files**. Full Python suite: **308 passed**. Final configuration/question route guard regression: **6 passed**.
- Strict TypeScript clean; UI unit suite: **37 passed**. Protocol and OpenUI regeneration hashes unchanged. Production static export and Electron build pass.
- Latest serial Windows checks: `npx tsx tests/phase5-desktop.ts`, `npm run test:desktop`, `npx tsx tests/phase4-files-desktop.ts` all pass. Phase 5 evidence records zero renderer errors.
- Supplemental `npx tsx tests/phase5-desktop.ts --other-inputs` passes: multi Other-only, rank with additional Other and key 4 selecting Other in the exhausted card; each actual model continuation contains the submitted text. `other-inputs-evidence.json` records zero renderer errors.
- `git diff --check` passes. Only the approved Phase 5 row/handoff changed in the constitution. Steps 1 through 5 have separate commits; Step 6 fixes/tests/docs and the approved roadmap update share the final phase commit.
