# Phase 4: Approvals inbox. Validation

Implementation approved on 2026-10-19. Product evidence is below; the exact constitution update in `roadmap-proposal.md` was approved by the user on 2026-10-19 and applied.

## Automated
- [x] `uv run --project backend ruff check backend` passes.
- [x] Final `uv run --project backend mypy --strict backend` and `uv run --project backend pytest backend/tests` after snapshot credential hardening: **278 passed**, strict mypy **84 files**.
- [x] `npm run typecheck` (`tsc --noEmit`) and `npm run test:ui`: **33 passed**.
- [x] Active `npm run test:desktop` baseline passes: Persian/English, real Demo read/OpenUI, replay, authentication, loopback binding, normal shutdown and forced development/packaged-engine cleanup. Run serially after builds; the earlier concurrent launch timeout was not reproduced.
- [x] `npm run generate:protocol`, `npm run generate:genui`, `npm run build`, `npm run build:electron` pass. Generated records/decisions/resolutions/RulesFile and `/approvals`, `/customize` static routes exist. Existing unsupported `outputFileTracing` option warns but does not fail the build; unrelated config is unchanged.
- [x] Installed SQLite/interrupt contracts and exact resume identity: `test_sqlite_interrupt_id_batch_mapping_and_reconstruction`.
- [x] Real graph approve/reject and continuation: `test_ask_interrupts_then_approve_writes`, `test_ask_then_reject_feeds_the_reason_back`; all three decisions also exercised in Electron.
- [x] Independent decisions, no effects before all answers, partial answers, original run reconstruction, monotonic replay and no duplicate publication: `test_pending_batch_partial_answer_restart_and_exactly_once`.
- [x] Actual engine process kills during a multi-call approval batch, during execution, and after command completion before durable result: `test_force_kill_engine_does_not_replay_effects[pending/executing/after-result]`. Observable launch count remains one; command PID is gone before recovery.
- [x] Graceful shutdown preserves pending work; Stop cannot execute after restart: recovery test above and `test_stopped_pending_run_cannot_execute_after_recovery`. Missing credential preserves pending records and restoration resumes: `test_missing_credential_preserves_pending_and_redacts_all_persistence`.
- [x] Approval/checkpoint/event reconciliation and torn final append: SQLite/recovery tests and `test_event_log_recovers_only_incomplete_last_append`. Completed/uncertain intents never redispatch: `test_journal_prevents_dispatch_after_uncertain_or_completed_effect`.
- [x] Fresh call-level retry, visible timeout, edit preview, reject and approved execution: `test_fresh_command_retry_can_be_edited_rejected_or_approved`; Electron retries the killed command with edited arguments through a new approval.
- [x] Auth and forged/stale/duplicate IDs: `test_approval_routes_require_auth`, `test_interrupt_route_reports_unknown_and_resolved_ids`, `test_resolve_records_the_answer_and_refuses_a_second_one`, stopped-run and concurrent recovery tests. Invalid schemas are refused before dispatch.
- [x] Edited arguments, traversal refusal and linked rule review: `test_edit_preview_revalidates_and_stages_allow_rule`. Existing permissions/rules/jail/Git tests cover Read-only, deny, protected paths, real symlinks/junctions, high-risk commands and mode ceilings; retained in the full suite.
- [x] Diffs/revisions for create/edit/delete, empty files, multiple hunks, CRLF, missing final newline and binary deletion: `test_diff_revision_binds_bytes_arguments_and_no_trailing_newline`, `test_unified_review_for_create_delete_empty_and_multiple_hunks`, `test_binary_delete_review_binds_original_bytes_without_decoding`; UI diff unit verifies old/new numbering. Electron checks stale review and byte-exact undo.
- [x] Checkbox rule is a separately reviewed proposal; reject/stale revision leaves rules unchanged: linked-rule regression above and `test_rules_proposal_reject_and_stale_revision_never_write`.
- [x] Rules API/grid, add/edit/remove validation, malformed-file protection, PUT staging and Auto review: `test_rules_routes`, `tests/unit/rules.test.ts`, files desktop script. Threaded proposals retain every record: `test_configuration_proposals_from_route_threads_do_not_overwrite_each_other`.
- [x] Branch/worktree gating and client-flag bypass prevention: `test_git`; actual worktree path equals reviewed path. Duplicate decisions cannot repeat effects. Electron covers branch failure and worktree-to-edit continuation.
- [x] Inbox filters, dimmed history, source metadata, selection, empty/error states: main desktop script against real engine data; no production mock rows.
- [x] ApprovalCard/DiffView OpenUI registration and shared deterministic views: generation/static export pass; actual cards/diffs render in Electron. Model-composed cards only resolve an existing engine-owned record by both IDs; unknown IDs expose no controls.
- [x] Badge/waiting state: inbox/rules unit tests include independent tasks, future schedule metadata, a remaining question after approval, partial decisions and duplicate replay. Electron covers two tasks/two workspaces and restart restoration.
- [x] Editing, rejected submissions, submission locking, labels/focus and safe Enter/Esc: UI unit tests plus desktop editor, shortcut and network-failure scenarios.
- [x] Canary model/edited inputs, rejection reasons, events and SQLite: `test_missing_credential_preserves_pending_and_redacts_all_persistence`. Diff/policy/Rules ledger: `test_review_redacts_current_file_diff_and_policy_before_checkpoint_payload`, `test_rules_diff_never_copies_existing_credential_into_approval_ledger`. Existing environment/tracing isolation tests remain green.
- [x] Final snapshot credential guard and regressions: `test_snapshots_refuse_registered_credentials_before_capture_and_restore`, guarded Rules-save failure and existing snapshot tests. Wired into graph snapshots, Rules saves and Undo; **30 targeted tests** and the full **278-test** suite pass. Metadata/content symlink escapes are refused; Rules Undo reviews exact prior bytes or prior absence.

## Manual / automated Windows Electron walkthroughs

Real Electron/preload vault/authenticated loopback API/SQLite graph/processes/filesystem. Provider fixture is local/offline; built-in Demo is also exercised. Generated evidence: `artifacts/phase4/`.

- [x] Built-in Demo `demo edit src/demo.txt: before => after` reads, requests edit, renders actual diff, and applies only after approval. Expanded/compact cards work; temporary modal removed. `phase4-desktop.ts`, `inline-fa.png`, `inline-compact-fa.png`.
- [x] Final reference-size visual rerun after selected-row hover fix passes. **1440×900** fa/en images inspected; `phase4-visual.ts` asserts selected hover color, 360px list, 240px sidebar, diff tints and narrow stacking. `reference-inbox-{fa,en}.png`, `reference-inbox-narrow-en.png`. Repeated runs distinguish pending fixtures from historical decisions. No invented plan metadata or agent reason.
- [x] Approve/edit/reject, optional reason returned to model, safe editor Enter/Esc, active-card Esc, shared inline/inbox resolution, dimmed history and all four tabs: main desktop script, `inbox-fa.png`, `history-fa.png`.
- [x] Multiple approvals across **two tasks/two workspaces**, newest-first decisions, badge and amber dots survive restart: main desktop script.
- [x] Force-kill while approvals wait; reopen without vault key, retain records and show actionable failure; restore key, quit normally, reopen and complete original runs. Subprocess case also kills after a partial answer in one barrier.
- [x] Force-kill running command after marker, reopen, inspect interrupted UI/model result and unchanged launch count. Explicit retry gets new 300-second review and edited arguments execute once. Main desktop script, `interrupted-fa.png`; process cleanup asserted by engine-kill tests.
- [x] Allow checkbox stages precise `src/**` rule; separate diff approved before save. Another rule proposal rejected unchanged. Backend regression verifies persisted matching rule behavior. Main desktop script and linked-rule test.
- [x] Customize chrome/Rules editing/refresh; actual Auto workspace still asks before another rule save and rejection preserves rules. Files desktop script, `rules-fa.png`, `rules-auto-en.png`.
- [x] Rules Undo routes through the inbox; rejection preserves current rules, approval restores prior absence. Files desktop script, `rules-undo-en.png`; backend tests also verify exact prior CRLF bytes.
- [x] Branch approve/reject/dirty-tree failure preserve expected HEAD/content. Worktree approval opens its run and separately gates edit; main checkout unchanged. UI undo restores original CRLF bytes. Files desktop script, `undo-en.png`, `worktree-en.png`.
- [x] Persian default, remembered English, mirrored shell, LTR paths/code, focus/keyboard and narrow view: desktop scripts and inspected images; logical-CSS unit passes.
- [x] Temporarily unavailable workspace remains in history and works after restoration. Missing key, empty inbox, stale file, API 503 and Stop exercised in main/files scripts. Stale rules revision covered by engine test. History retained.

## Exit criteria
- [x] Final quality/snapshot/visual checks above complete; every R1–R14 has passing evidence. No unsupported completion claim.
- [x] `learnings.md` records installed versions, persistence ordering, recovery races, intentional choices, limits and handoff. No new unresolved TODO markers.
- [x] Exact roadmap row/handoff approved by the user on 2026-10-19, applied and committed with final phase changes. Steps 1 through 5 have separate commits; Step 6 fixes/tests/docs and the approved constitution update share the final commit under AGENTS.md.

No live provider key or external endpoint is required. Only the approved Phase 4 completion row and handoff changed in the constitution.
