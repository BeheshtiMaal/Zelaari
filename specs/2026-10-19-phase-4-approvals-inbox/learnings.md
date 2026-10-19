# Phase 4: Approvals inbox. Verified learnings

Final implementation and verification evidence is maintained in `validation.md`. The constitution completion proposal remains separate until the user approves it.

## Installed contracts (Step 1)
- Inspected installed source on 2026-10-19: deepagents 0.7.28, LangGraph 1.2.16, langgraph-checkpoint-sqlite 3.1.2, LangChain 1.4.6.
- `interrupt()` restarts its node. Multiple interrupts inside one task are matched by position, and only the first unanswered one is exposed. The Phase 3 loop cannot expose an entire pending set at once.
- Keep the pre-tool permission barrier, but expose all approvals from that model turn in one graph interrupt envelope. Each decision is independently keyed and validated by tool-call ID; the resume map is keyed by the actual graph interrupt ID. This is not one shared approval for a batch.
- `test_sqlite_interrupt_id_batch_mapping_and_reconstruction` proves the installed SQLite saver restores the exact interrupt ID and accepts reverse-order independent decisions after graph reconstruction.

## Persistence ordering to implement
1. Checkpoint pauses before approval publication; reconstruct missing publications from checkpoint interrupts after a crash.
2. Store approval/decision atomically before emitting its event; reconcile missing events by stable identity after restart.
3. Resume only a fully answered barrier; stable call IDs prevent answer reassignment.
4. Journal side-effect intent before dispatch and its result before returning to the graph. Recovered incomplete intents become interrupted results; never redispatch uncertain effects.
5. Rules proposals bind to a content revision; approval executes exactly that revision or requires refreshed review.

## Scope notes
No constitution changes applied. The approved plan's final roadmap update still needs explicit approval of its exact text.

## Steps 2–3 evidence
- Recovery regression exposed an event/checkpoint race: publishing inside the stream's interrupt update could precede checkpoint completion. Publication now follows stream closure/state inspection with `durability="sync"`.
- Real graph tests restore a partially answered two-call barrier, reject one call, approve the other, preserve event sequence and execute only the approved write.
- Edited arguments require a refreshed preview and content revision. The graph wrapper rechecks schema, jail, current rules and reviewed contents before dispatch.
- Effect journals cache completed tool results; incomplete intents return an interrupted tool result without executing. This covers writes/deletes as well as commands.
- Rules PUT now stages an explicit proposal. Checkbox rules are separate linked proposals; graph edit and rule-change decisions are tested independently.
- Branch/worktree client boolean flags no longer constitute authorization. Their proposals are durable configuration actions decided through the interrupt endpoint.
- Focused permission/recovery/review/rules/Git suite: 80 passed; added edit-preview/linked-rule regression also passes. Strict mypy and ruff pass at this step. Full phase validation is still outstanding.

## Final implementation details
- Per-run reconstruction metadata, provider identity and approval ledger live beside events under `.harness/runs/<id>/`. Provider metadata contains references, never credentials. Missing vault credentials or changed provider identity block reconstruction while keeping decisions available. Electron rehydrates keys through its existing vault path.
- Configuration approvals use `.harness/action-approvals.json`: Rules, branch changes, worktree creation and explicit command retry need no model thread. Route-thread mutations are serialized; asynchronous command completion reloads the ledger before updating its record, preserving concurrent proposals.
- Original branch/worktree boolean flags are accepted for wire compatibility but do not authorize execution. Worktree creation reserves its ID before review, creates the exact reviewed path, and returns the created run ID so the UI opens that run and separately reviews its file edits.
- A restart UI race exposed a decision before the graph finished rebuilding. Decision resolution now waits for the restored permission barrier to become available.
- Graceful manager shutdown cancels execution while preserving resumable state; explicit Stop cancels approvals and emits a terminal stopped event. Event replay reloads existing sequence numbers, fsyncs appends and truncates only a torn final record; complete malformed records are refused.
- Journaling covers filesystem mutations and commands. A completed intent returns its stored result; an uncertain intent returns an interrupted result to the model. No uncertain action is redispatched. The UI offers a fresh retry proposal with visible timeout and editable arguments, rather than synthesizing a new task prompt.
- Preview revisions bind tool/arguments, raw pre-edit bytes and the resolved target path. Both API confirmation and tool dispatch recheck them. The existing file-edit tool reads with universal newline conversion; the preview mirrors that actual operation. Editing can normalize CRLF to LF; Undo restores the original bytes exactly. Binary deletion gets a bounded summary and byte-bound revision.
- Diff/policy payloads are redacted before graph interrupts and before preview/ledger persistence. Rejection reasons and tool results are redacted before checkpoints. Snapshot capture and restore refuse registered UTF-8/UTF-16 credentials before mutation, instead of copying credentials into snapshots.
- Snapshot metadata targets and the actual metadata/content artifact paths are jailed, including real symlinks. Rules Undo cannot use the ordinary direct-revert path: it creates a durable Rules approval, and the renderer opens that proposal. Approval restores exact captured bytes or prior file absence; rejection leaves current rules intact. This closes an otherwise indirect bypass of the always-ask rule.

## UI and deliberate scope choices
- ApprovalCard and DiffView are registered in the Zod OpenUI library and shared by deterministic inline/inbox views. Model-composed approval controls can reference only an actual engine-owned record by both IDs.
- Inbox state is authoritative server data refreshed every 1.2 seconds. Counts are derived from pending approvals, not increment/decrement counters. Task waiting metadata reserves both `approval` and `question`; schedule source metadata is supported without implementing a scheduler.
- The allow-rule checkbox stages a separate explicit rule-change review. This is the approved R10 design and enforces the constitution's always-ask rule; checking it never silently changes permissions.
- The mocked Customize chrome is retained. The Rules inner grid was not drawn, so it uses the existing schema and shared design tokens. Other Customize tabs remain unavailable for their assigned phases.
- Main's expanded amber review and Run's compact review/open-in-inbox treatment are both available. No fake agent reason, in-plan status, step count or schedule is manufactured. Plan metadata remains Phase 6.
- Built-in Demo supports `demo edit <relative-path>: <old text> => <new text>`: it reads first, then requests the real edit. This makes approval validation available without a provider key or network.
- The final visual pass uses real pending Demo approvals at CSS 1440×900, asserts the 360px list/240px sidebar and diff tints, and captures fa/en plus a narrow viewport. A generic button hover rule initially obscured the selected row's teal background; an explicit selected-row hover rule fixes it.
- Native input controls keep their keyboard behavior; Enter/Esc decisions are scoped to a focused review outside editable controls. Submission locks prevent double activation. API failure, changed contents, unavailable workspace and missing credential remain recoverable states.

## Verification and retained limits
- `test_engine_kill_recovery.py` kills actual engine processes mid-interrupt, during a command, and after process completion before durable result. Command launch count stays one, and the original command process is gone before recovery.
- `phase4-desktop.ts` drives the real vault, compatible local fixture provider and graph across two workspaces; it exercises edit/reject/linked-rule flows, app/engine restarts, missing credential/workspace, interrupted command and fresh edited retry.
- `phase4-files-desktop.ts` uses built-in Demo for byte-exact Undo, stale/network errors, Stop, branch failures, isolated worktrees, Auto rule review and Rules Undo approval. `phase4-visual.ts` supplies reference-size layout evidence. Generated screenshots/evidence are in `artifacts/phase4/` and are not committed.
- The earlier `phase3-desktop.ts` is a historical script targeting the removed modal. Its approval/branch/worktree/undo behaviors are covered by the Phase 4 scripts. The active `test:desktop` baseline was updated for the real preload capability list and newly enabled sidebar pages.
- Installed Next.js 16.4.2 still warns about the pre-existing `outputFileTracing` option. Static export succeeds; this phase does not silently change unrelated configuration or claim remote CI execution.
- Existing bounded file/snapshot sizes and workspace-jail race/alias limitations remain. This is not an OS sandbox. Question tools, planning/deviation gates, scheduler, remaining Customize content and packaging delivery retain their assigned phases. No new unresolved TODO is left outside this record.

## Handoff
Phase 5 should extend the durable barrier to question answers while retaining exact identities and the all-required-answers gate. Keep questions inline and out of the approval badge, preserve credential rehydration and no-replay journals, and use `TaskRecord.waiting_on` for mixed waiting states. Apply only the approved completion row/handoff from `roadmap-proposal.md`; never rename or reorder later phases.
