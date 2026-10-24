# Phase 6: Planning and activity timeline. Validation

Status: **Passing.** Every box below is backed by the run recorded in "Final evidence" and `learnings.md` Step 6. Only the roadmap completion row remains, and it requires explicit user approval before it is applied.

## Final evidence

Settled source, single sequential run per gate on Windows, no concurrent type-check/build processes:

| Gate | Result |
| --- | --- |
| `uv run --project backend ruff check backend` | All checks passed |
| `uv run --project backend mypy --strict backend` | Success, 127 source files |
| `uv run --project backend pytest backend/tests` | **417 passed**, 2 warnings, 405 s |
| `npm run typecheck` | passed |
| `npm run test:ui` | 44 passed |
| `npm run generate:protocol` + `npm run generate:genui` | passed, `git status` unchanged (deterministic) |
| `npm run build` | passed, 6 static routes |
| `npm run build:electron` | passed (`electron-dist/main.cjs`, `preload.cjs`) |
| `npm run test:desktop` | passed: Persian/English, real demo read + OpenUI, replay, auth, loopback, normal and forced cleanup |
| `tests/phase4-desktop.ts` | passed, 12 steps (vault, demo edit, parallel approvals, rules, background restart, vault-loss force-kill, offline workspace, command force-kill, retry, English/narrow) |
| `tests/phase5-desktop.ts` | passed, 8 steps (question dock, batch/multi/rank, validation/IME, mixed barrier, force-kill recovery, grill, exhausted/stop/decline) |
| `tests/phase6-desktop.ts` | passed, 10 scenarios, no renderer errors |

Named Phase 6 suites: `test_planning_contracts`, `test_planning_policy`, `test_planning_settings`, `test_planning_gate`, `test_planning_progress`, `test_plan_revision_graph`, `test_plan_publication`, `test_plan_review_recovery`, `test_activity`, `test_readonly_delegates`, `test_delegate_recovery`, `test_summary_privacy`, `test_steering`, `test_stop_lifecycle`, plus the real-graph factory cases in `test_factory_*`.

Artifacts: `artifacts/phase6/evidence.json`, `run-fa.png`, `run-en.png`, `run-en-narrow.png`, `plan-review-fa.png`, `finished-fa.png`, `actual-summary-fa.png`, `read-only-denial-en.png`; `artifacts/phase4/evidence.json`; `artifacts/phase5/evidence.json`.

## Automated
- [x] R1: bounded plan/step/glob/verify/config schemas reject malformed, duplicate, empty, traversal and invalid enum inputs. Plan submission alone executes nothing. New mutations/commands without accepted plan/active step fail closed; read-only analysis/questions still work.
- [x] R2–R3: threshold matrix covers 3/4 steps, 3/4 distinct files, configurable boundaries, overlapping globs, literal new targets, uncertain/wide expansion and high-risk declaration/classified verify command. Ask and Read-only gate qualifying plans; Auto skips only initial review; Read-only cannot gain writes. High-risk trigger cannot be disabled outside Auto.
- [x] R3: effective workspace config load/defaults/bounds, preservation of unrelated keys and malformed-file protection. Save asks even in Auto; reject/stale preview/no-key/restart preserve old config; approve changes exactly reviewed fields with snapshot/redaction protection. Protected config cannot be edited through a bypass.
- [x] R4: real graph approve/edit/reject for initial/revised plan, stale revisions, wrong IDs, duplicate decisions and rejected initial plan preventing effects. A plan decision shares the mixed barrier with a question/tool approval; partial answers survive SQLite reconstruction in either order and siblings wait for all requirements.
- [x] R5: Ask and Auto gate out-of-scope mutations, a dropped step and the third added step. Cover two additions without review, incremental one-step attempts, reorder/rename, changed risk/verify/scope, empty globs, jail escapes, rejected changes and disabling the deviation toggle without disabling ordinary permissions.
- [x] R6: `write_todos` maps to stable accepted IDs, validates status/active-step rules, preserves completed history and cannot bypass plan revision gates. Parent step completion waits for running child work. Legacy/unscoped history stays readable without invented plans.
- [x] R7: typed parent/step/child event ordering, stable IDs and a single monotonically ordered run stream with interleaved concurrent delegates. Reconnect/replay reproduces exact state, and child finish never terminates the parent.
- [x] R8: PlanChecklist is generated/registered and shared; forged, unknown, cross-run or stale model-composed references cannot create accepted scope/progress/decisions. Automatic adoption and human approval render distinctly. Existing malformed GenUI fallback works.
- [x] R9–R10: completed-step summary counts/durations and expansion state derive from actual events; active step expands; Thinking auto-collapses once on step end and can be reopened. Several turns/steps/delegates with reasoning on only some preserve exact attribution; answer prose is never reasoning; no-reasoning text appears only at the appropriate completed boundary.
- [x] R11: reviewer/researcher really execute concurrently; write/edit/delete/command/settings/nested/unknown-agent paths are denied even under Auto and permissive parent rules. Parent worktree jail, real symlink/junction escapes, errors, results, cancellation and interrupted child recovery are tested.
- [x] R12: installed summarizer really changes history under a lowered test threshold; actual operation/count produces one durable notice, while model prose/fake markers do not. Summarizer/delegate input/output canaries are absent from SQLite/events/storage; replay preserves old activity.
- [x] R13: latest-request context usage differs correctly from cumulative run usage, marks estimates/fallback window, handles absent data and drives only real bar values. Real/unavailable limit telemetry is distinguished; waits and badges retain approval/question semantics across tasks and replay.
- [x] R14: authenticated steering API validates bounds, duplicate client IDs, unknown/terminal runs and run identity; queued/delivered acknowledgement is durable. Several messages inject once in order at a safe boundary; paused mixed decisions remain required. Scope steering still invokes deviation review. Failed submit preserves draft; Enter/Shift+Enter/picker/question shortcuts and Stop remain separate.
- [x] R15: Stop acknowledged/emitted within 1 s while reasoning, tool execution, pending decisions, queued steering and parallel delegates run; no late effects/results and owned processes terminate. Graceful close preserves resumable state. Actual force-kill during plan review, partial mixed decisions and delegated activity restores original run/provider/worktree, queued messages and completed results without automatic replay of uncertain effects.
- [x] R15: secret canaries in plans/reviews/config previews, steering, parent/child reasoning/results and summaries never enter logs/events/ledgers/checkpoints/workspace artifacts. Existing environment/tracing/credential protections remain green.
- [x] R16: strict Python gates pass: `uv run --project backend ruff check backend`, `uv run --project backend mypy --strict backend`, `uv run --project backend pytest backend/tests`; include existing permission/approval/question/recovery regressions and executable offline agent scenarios.
- [x] R16: strict TypeScript/UI checks and deterministic generation pass: `npm run typecheck`, `npm run test:ui`, `npm run generate:protocol`, `npm run generate:genui`, `npm run build`, `npm run build:electron`; logical CSS and diff checks pass.

## Manual / automated Windows Electron walkthroughs
Use real Electron/preload/authenticated loopback engine/SQLite, disposable workspaces/profiles and offline Demo/local provider fixtures. Save generated evidence under ignored `artifacts/phase6/`; no external credential is required.

- [x] Run/Main at CSS 1440×900 match hierarchy/tokens: header/status/elapsed/tokens/Stop, compact finished rows, expanded active teal step, plan checklist, reasoning/delegates/inline approval, subdued summary notice and 288–300px right panel. Inspect Persian default, remembered English and narrow layouts without inaccessible content or horizontal overflow.
- [x] Exercise small auto-adopted, large/high-risk reviewed and Auto initial plans. Approve an edited plan; reject another and confirm no out-of-plan effect. Review ordered plan/diff/metadata and separately required file/command approval. Counts, inbox badges and questions remain synchronized.
- [x] Change step/file thresholds and deviation toggle for a selected workspace; approve/reject config saves, restart and inspect effective values. Trigger outside-glob edits, two/three cumulative additions and a dropped step under Ask/Auto; rejection preserves accepted scope.
- [x] Complete a real multi-step task; verify progress/checklist, accurate counts/durations and collapsed rows. Expand old steps while new deltas arrive; manually reopen ended Thinking; observe actual reasoning on one step and no-reasoning text on another without fabricated content.
- [x] Launch reviewer/researcher concurrently against local fixture docs/source; inspect read-only badges, delegated tasks, mini timelines, actual results, durations and independent collapse controls. Attempt a forbidden child write/command; inspect denied result and unchanged workspace.
- [x] Exercise an actual summary operation with a test-configured low threshold and inspect notice/source/count, real/unavailable context and limits states. No production mock metrics appear.
- [x] Type steering while a delegate/tool runs and while question/approval waits. Inspect queued/delivered state and original-run continuation; submit a duplicate and simulate a failed request without losing draft. Steering outside scope requests review and never answers the waiting question/approval.
- [x] Use header and composer Stop; confirm immediate terminal UI, cancelled children/decisions/messages, no late mutations and no orphan processes. Close/reopen and force-kill pending-plan/mixed/delegate runs; restore original identity, history and independent remaining decisions safely.
- [x] Verify keyboard/focus/ARIA for step/Thinking/child disclosure controls and mid-run composer, IME/Enter/Shift+Enter/Esc isolation, reduced motion, Persian digits and LTR code/paths. Recheck existing `/grill`, inline questions, approvals/edits/rejections, Rules always-ask, worktree and Undo.
- [x] Active `npm run test:desktop` baseline and relevant existing Phase 4/5 Electron regressions pass against final build; no renderer errors, auth regressions or normal/forced lifecycle leaks.

## Exit criteria
- [x] Every requirement R1–R16 has passing named evidence; every automated and Windows check above is supported by actual results, with no unresolved spec/mock conflict.
- [x] `learnings.md` records installed API proofs, persistence ordering, gate/count/identity choices, telemetry limits, scope boundaries and Phase 7 handoff. No new unresolved TODO lacks an entry.
- [x] Exact roadmap completion row/handoff explicitly approved, applied and committed with final phase changes. Each earlier plan step has its own commit; later phases retain their names/numbers/order.
