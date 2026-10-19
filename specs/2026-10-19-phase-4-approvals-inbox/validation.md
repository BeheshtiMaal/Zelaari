# Phase 4: Approvals inbox. Validation

Status: **Draft — not executed.** Every box needs evidence before completion.

## Automated
- [ ] `uv run --project backend ruff check backend` passes.
- [ ] `uv run --project backend mypy --strict backend` passes.
- [ ] `uv run --project backend pytest backend/tests` passes, including prior phase regressions.
- [ ] `npm run typecheck` (`tsc --noEmit`) and `npm run test:ui` pass.
- [ ] Protocol/GenUI generation is reproducible; `npm run generate:protocol`, `npm run generate:genui`, `npm run build` and `npm run build:electron` pass.
- [ ] Installed-contract proofs exercise real SQLite checkpoints, exact interrupt IDs and per-call answer mapping (R1–R3).
- [ ] Real graph approve executes exactly once; reject with/without reason returns a tool result and permits model continuation (R5/R6).
- [ ] Parallel gated calls produce distinct approvals; no gated effect occurs until all answers exist; each call uses its own answer and allowed calls do not repeat (R2).
- [ ] Kill/restart engine while waiting, including after one of several answers: pending IDs, decisions, history and SSE sequences survive; final answer resumes the original run once (R1–R3).
- [ ] Graceful shutdown preserves waiting runs; explicit Stop prevents later execution; missing model/key/workspace blocks safely and restoration permits recovery (R3).
- [ ] Fault injection at approval/checkpoint/event reconciliation boundaries creates no lost decision, duplicate approval or repeated side effect (R1–R4).
- [ ] Kill after command intent, during command execution, and after process completion before durable result: original command never launches again; UI/model receive interrupted outcome; completed sibling effects are not repeated (R4).
- [ ] Explicit command retry, including longer timeout, creates a new reviewed call with visible timeout; reject leaves it unexecuted (R4/R6).
- [ ] Missing/wrong auth, foreign run/interrupt IDs, duplicate/racing submissions, invalid actions/arguments and resolved/stopped decisions cannot execute tools (R5/R14).
- [ ] Edited command/file inputs execute the approved valid arguments; traversal, symlink/junction escape, protected paths, explicit deny, Read-only and increased risk cannot inherit prior approval (R6/R14).
- [ ] Unified diff handles create/edit/delete, multiple hunks, empty files, CRLF and absent trailing newline; line numbers/tints are correct; stale contents force refreshed review; snapshots/undo preserve prior bytes (R7).
- [ ] Checkbox stages an exact tool/path allow-rule proposal; rules remain unchanged until linked approval; approve writes atomically, reject does not; stale revision refreshes; boundaries remain enforced in Ask/Auto/Read-only (R10).
- [ ] GET/PUT Rules grid supports validated add/edit/remove; direct PUT cannot bypass approval; save/reject/refresh preserves correct effective permissions and malformed-file protections (R11).
- [ ] Branch/worktree actions remain gated after temporary modal removal; restart and duplicate decisions cannot repeat their effects (R9).
- [ ] Inbox status filters, dimmed history, source metadata, selection and empty/error states reflect actual durable data (R8).
- [ ] OpenUI renders ApprovalCard/DiffView and routes actions by validated identity; inline and inbox resolve the same record once (R9).
- [ ] Badge counts pending approvals across multiple tasks/workspaces and synthetic future schedule metadata; questions excluded; mixed waiting-kind fixtures retain amber dot; replay/reconnect adds no duplicates (R12).
- [ ] UI tests cover input edit/review, rejected submissions, button locking, labeled controls, focus and shortcuts; typing Enter/Esc in editable controls never submits (R13).
- [ ] Canary credentials, including edited inputs/rejection reasons, do not leak into API approval data, logs, events, checkpoint SQLite, journal or fixtures; existing environment/telemetry isolation tests stay green (R14).

## Manual (Windows Electron, real engine and static export)
- [ ] Offline demo proposes a file edit: amber inline card, real diff, review and inbox navigation work; no temporary approval modal remains.
- [ ] Inbox at reference 1440×900 matches Inbox.dc.html hierarchy, copy, colors, list/detail proportions, chips, snapshot note, checkbox and actions. Inspect saved screenshots.
- [ ] Compare inline expanded/compact cards with Main.dc.html and Run.dc.html; no fake plan status, reason, step counts or schedule rows appear.
- [ ] Approve, edit then approve, and reject with an optional reason through actual UI; verify filesystem/command result and model continuation. Duplicate clicks do not duplicate effects.
- [ ] Queue multiple approvals across two tasks/workspaces; decide in reverse order using inline and inbox. Tabs/history, global badge and per-task waiting dots remain accurate.
- [ ] Force-kill engine mid-interrupt and reopen app; inspect original pending approvals, answer and finish the original run. Repeat with partial decisions and normal app quit.
- [ ] Force-kill engine during a harmless long-running command with an observable launch marker; reopen, confirm interrupted card/model result and unchanged launch count. Retry explicitly with a fresh approval. No orphan process survives.
- [ ] Check the allow-rule box for an edit under src/**; review the separate linked rules diff, approve, inspect rules and test a later matching edit. Reject another rule proposal and confirm unchanged rules.
- [ ] Customize Rules chrome matches Skills.dc.html; edit tool/path rules, approve/reject, reload and verify actual enforcement, including rule changes in Auto.
- [ ] Branch switch/worktree creation and snapshot undo still work through real desktop flows without bypassing review.
- [ ] Persian first launch and remembered English setting both render correctly; logical layout mirrors, code stays LTR, policy reasons localize, keyboard/focus are usable and narrow windows keep both panes accessible.
- [ ] Empty inbox, missing workspace/model credential, changed file/rules revision, decision API failure and stopped run show actionable states without losing history.

## Exit criteria
- [ ] Every requirement R1–R14 has passing test/manual evidence above; no unchecked items or unsupported completion claims.
- [ ] learnings.md records verified installed APIs/versions, recovery guarantees, deviations, limitations and every deferred TODO.
- [ ] Exact roadmap completion/handoff change approved by the user, applied and committed with phase work; one clear commit per ordered plan step.

No checks are claimed complete at spec time. Live-provider access is not required: deterministic offline graph/desktop fixtures cover this phase's permission and durability behavior.
