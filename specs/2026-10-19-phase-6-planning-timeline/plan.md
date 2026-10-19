# Phase 6: Planning and activity timeline. Plan

Status: **Approved by the user; implementation in progress.**

Implement in order after approval, one commit per completed step. First verify installed package contracts with executable proofs and record them in learnings. If actual behavior contradicts the spec, update it before proceeding; propose and obtain approval for any constitution change.

## Step 1: Verify graph contracts and define planning/activity schemas
- Inspect installed `create_deep_agent`, `TodoListMiddleware`/`write_todos`, middleware ordering, child tool configuration, subgraph streaming/namespace identity, summarization hooks and SQLite resume. Prove real concurrent child activity, enforced read-only behavior and a summarization transition without effectful interrupt replay.
- Specify bounded plan/step/revision, concrete-file count, planning configuration, scoped activity/reasoning/context telemetry, steering/acknowledgement and compatible human-decision contracts. Define todo-to-step identity and timing/count semantics explicitly.
- Define authenticated route/error contracts and regenerate protocol types. Add schema and real SQLite/mixed-barrier proofs; record verified source versions/APIs and the safe steering boundary.

## Step 2: Implement structural plan/progress/deviation gates
- Add `submit_plan` and prompt rules; require an accepted active plan before new mutations/commands while retaining read-only analysis/questions and grill readiness.
- Implement default/configurable thresholds, high-risk trigger, conservative distinct-file counting and small/Auto adoption. Persist plan revisions and route reviews through the existing mixed human barrier and shared approval APIs.
- Implement `write_todos` identity/progress adaptation, cumulative addition/drop/scope deviation detection and pre-dispatch revalidation in Ask/Auto. Preserve ordinary permission, jail, snapshot and effect-journal checks.
- Add workspace config load/merge/validation and always-reviewed config-save actions; bind edited plan/config previews to current revisions. Test all decision/mode/threshold/config/forged-progress paths and partial mixed recovery.

## Step 3: Implement real delegated activity, reasoning and context instrumentation
- Configure only authorized reviewer/researcher delegation with strict read-only tools/permissions and parent workspace/worktree containment. Close stock/default-agent, command, nested-delegation and protected-state bypasses.
- Translate actual parent/subgraph lifecycle into typed scoped start/action/reasoning/result/finish events. Keep a single durable run sequence and stable invocation/step identities across parallel execution and reconstruction.
- Instrument actual summarization/offload state changes, redact all summary/delegate paths and collect latest-request context metadata separately from cumulative token usage. Derive timestamps/counts from observed activity.
- Test parallel ordering, several simultaneous delegates, child denials/errors, per-step/per-child reasoning absence, actual summary operations, replay and cancellation. Use local fixture documentation, without adding web research.

## Step 4: Add durable steering and complete runtime lifecycle
- Add authenticated, idempotent queued-message API/storage and safe exactly-once parent-model injection. Queue while tools/delegates/barriers run; do not start another invocation or use a message as a human decision.
- Reconcile queued/delivered messages, plan/progress decisions and scoped events after real app/engine termination; preserve original credentials/worktree/provider and completed child results. Mark interrupted activity and retain no-replay effect safety.
- Cancel parent/delegate work and block late dispatch on Stop; acknowledge under one second. Test missing dependencies, mixed decision/steering order, send/Stop races, duplicate delivery, process-tree cleanup and secret persistence.

## Step 5: Build shared PlanChecklist and the Run/Main timeline
- Register trusted OpenUI PlanChecklist; add typed reducer/services/hooks for plans, scope, grouping, reasoning, timing, counts, child activity and user expansion preferences. Keep business logic out of components.
- Rebuild Run's collapsed finished/expanded active steps, Thinking panels, concurrent sub-agent blocks, summary notices and inline approval; retain Main's expanded plan/diff/docked question treatment using shared data/components.
- Add truthful header/status/elapsed/tokens and right-panel plan/delegates/context/limits/waits; expose unavailable data without mock metrics. Connect real plan metadata to approval details.
- Connect mid-run editable composer/steering acknowledgement and Stop action; add only phase-owned workspace planning controls to Settings > Permissions with durable configuration review.
- Test collapse/auto-collapse/manual re-expansion, live updates/replay, failed submissions, shortcut isolation, accessible semantics, fa/en, logical CSS/reduced motion and narrow layout.

## Step 6: Validate Windows scenarios and record handoff
- Run every automated and Windows scenario in validation, including real killed-engine recovery, parallel read-only agents, actual summarization, partial reasoning, steering and Stop latency.
- Inspect reference-size Run/Main screenshots in Persian/English plus narrow views; run appropriate existing approvals/questions/Rules/worktree/Undo and baseline lifecycle regressions. Record exact evidence and remaining limits in learnings; tick only passing checks.
- Propose exact Phase 6 completion row/handoff without changing later phase order. After explicit constitution approval, apply and commit with final phase changes. Phase 7 receives plan/activity identities, safe steering, truthful context/limits contracts and existing question/exhaustion integration; do not implement its verify/fix/context policy here.
