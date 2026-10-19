# Phase 4: Approvals inbox. Plan

Status: **Approved on 2026-10-19. All six steps complete; final validation passes and the roadmap completion update is approved.**

Work in order; commit each completed step separately with its relevant tests. If verified behavior contradicts this spec, stop implementation and update the spec first. Constitution changes require explicit user approval.

## Step 1: Verify installed contracts and define durable protocol
- Inspect installed LangGraph, deepagents and middleware source for interrupt IDs, per-call resume mapping, SQLite state reconstruction and node replay. Record exact versions/shapes and focused executable proofs in phase learnings.
- Define typed approval records, decisions/edited arguments, source metadata, policy codes, recovery states and command intent/result records. Extend generated TypeScript protocol and OpenUI contracts; never hand-copy wire types.
- Specify transaction/reconciliation ordering across approval storage, checkpoint, event log and command journal, including recovery at each boundary. Use existing app-data workspace discovery and workspace checkpoint layout.

## Step 2: Implement durable pending sets, API and restart recovery
- Replace single in-memory pending/answer slots with durable per-interrupt records and persisted partial answers. Add authenticated listing/filtering and validated decision submission.
- Reconstruct graph/run/event state and pending sets after restart, hydrate credentials through existing vault flow, and resume only when required decisions are complete.
- Separate graceful shutdown preservation from explicit Stop. Reconcile persisted events/history without duplicate announcements or repeated effects.
- Test real demo graph approve/reject, parallel calls, partial-answer restart, missing dependencies, stale decisions, event replay and stop.

## Step 3: Enforce edit, crash and rule-change safety
- Journal command launches/results and reconcile incomplete intents to interrupted tool results without re-execution. Route explicit retries through new call-level approval with visible arguments/timeout.
- Build current-content diffs and stale-content checks; validate edited inputs against schema, jail, rules, mode and risk. Preserve snapshots and exact call identities.
- Stage Rules API and checkbox-generated rule changes as durable explicit approvals. Support decisions for configuration actions without requiring a model run; bind them to workspace/revision and audit source. Avoid recursive rule approvals.
- Unify temporary branch/worktree review with durable approval handling, retaining pre-execution permission rechecks.
- Test all new permission paths, crash windows, rejected/stale rule writes and secret persistence boundaries.

## Step 4: Implement shared OpenUI approval surfaces and inbox
- Add ApprovalCard and DiffView to the Zod library and generation flow. Keep decision state, API calls, diff preparation and permission logic in typed stores/services.
- Build the real-data inbox with panes, tabs, list previews, detail review, input editing, optional rejection reason and staged rule checkbox.
- Replace temporary inline modal with mock-aligned amber cards and inbox navigation. Add localized policy explanations, sensible empty/error states, submission locking and scoped shortcuts.
- Test rendering/actions, line numbering, edits, failures, resolved history and synchronized inline/inbox decisions.

## Step 5: Add Rules hub and global indicators
- Build Customize chrome with the Rules grid, workspace selection, defaults, rule edits and pending-save review. Keep other hub content deferred.
- Derive badge/waiting dots from durable state across tasks/workspaces, refresh after background decisions and restore after app launch.
- Test rule editing/rejection and badge/replay/mixed waiting-kind behavior; preserve existing workspace, branch, worktree and undo flows.

## Step 6: Complete validation and handoff
- Run every automated gate and every Windows manual scenario in validation.md, including force-killed engine recovery and inspected Persian/English screenshots against the mocks.
- Tick only checks supported by named tests or artifacts; record verified package APIs, deviations and remaining limitations in learnings.md.
- Propose the exact roadmap Phase 4 completion row/handoff for approval before modifying the constitution; commit approved changes with the final phase work. Preserve later phase ordering and scope.
