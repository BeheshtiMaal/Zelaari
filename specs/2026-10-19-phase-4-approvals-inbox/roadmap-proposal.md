# Phase 4 roadmap completion proposal

Approved by the user on 2026-10-19 and applied to `specs/roadmap.md` in the final phase commit.
This changes only the Phase 4 row and adds its handoff; later phases retain their existing names, numbers and order.

## Replace the Phase 4 row with

| 4 | **Approvals inbox - complete** | Durable SQLite approval barriers, approve/edit/reject, unified diffs, linked allow-rule review, Rules grid, global counts and waiting dots, restart recovery and no replay of uncertain effects. Offline demo and Windows Electron evidence recorded in `2026-10-19-phase-4-approvals-inbox/validation.md`. | Approvals inbox |

## Append after the Phase 3 handoff

## Phase 4 handoff to Phase 5

Phase 4 is complete; validation and verified package/recovery behavior are recorded in
`2026-10-19-phase-4-approvals-inbox/validation.md` and `learnings.md`. Phase 5 inherits durable
approval records, a pre-tool graph barrier with independently keyed decisions, edited-input previews
bound to current file contents, command/effect journals, replayable events, shared OpenUI approval
components and a Rules editor. Extend the barrier for question answers while preserving tool-call
identity and the rule that execution waits for all required answers. Questions stay inline and never
increase the approvals badge; `TaskRecord.waiting_on` already reserves the `question` kind. Preserve
credential rehydration and original provider identity checks on recovery, and never redispatch an
incomplete effect intent. User-initiated Rules, branch, worktree and retry actions have durable
configuration approvals without a model thread. Schedule production remains Phase 9b; plan metadata
remains Phase 6. Existing workspace-jail race/alias limitations remain documented; this is not an OS sandbox.
