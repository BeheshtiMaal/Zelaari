# Roadmap proposal (Phase 3)

Per AGENTS.md rule 5 the constitution is not edited silently. These are the only changes I want to make to
`specs/roadmap.md`, proposed for approval with this phase's spec. Nothing else in the constitution changes.

## 1. Phase 3 row — name the approval modal and the two error states

Current:

```
| 3 | Tools + permission layer | fs tools + `run_command`, workspace jail, atomic writes, snapshots/undo, rules.json, modes, risk classifier, branch chip (`git switch` via approval), Worktree option, Workspace page | Workspace (files + tasks) |
```

Proposed:

```
| 3 | Tools + permission layer | fs tools + `run_command` (Job Object kill), workspace jail, atomic writes, snapshots/undo, rules.json, modes, risk classifier, interrupt plumbing + temporary approval modal, branch chip (`git switch` via approval), Worktree option, Workspace page, command-timeout and jail-block error states | Workspace (files + tasks), Errors (2 of 6) |
```

Reason: `ask` cannot work end to end without a modal, so it belongs to Phase 3 (the phase brief says so), and
the two error cards are produced by Phase 3's own failures.

## 2. Phase 4 row — interrupts start in Phase 3

Current:

```
| 4 | Approvals inbox | interrupts, ApprovalCard + DiffView, approve/edit/reject, allow-rule checkbox, resume after restart, Rules tab | Approvals inbox |
```

Proposed:

```
| 4 | Approvals inbox | durable interrupt persistence, ApprovalCard + DiffView, approve/edit/reject, allow-rule checkbox, resume after restart, Rules tab | Approvals inbox |
```

Reason: Phase 3 delivers the interrupt mechanism and a minimal approve/reject modal; Phase 4 delivers the
durable inbox, edit-input, allow-rule checkbox, restart resume and the Rules tab. Without this edit the two rows
read as if Phase 3 ships no interrupts at all.

## 3. Phase 9 row — remaining error states only

Current phase 9 outcome ends with `... Empty; Errors`. Proposed: `... Empty; Errors (remaining 4 cards)`.

Reason: Phase 3 owns the timeout and jail cards because it produces those failures; Phase 9 keeps 401/429,
engine crash, fix-attempts-exhausted and no-tool-support.

## 4. Handoff paragraph — append one sentence

Add to the end of the "Phase 0 handoff to Phase 1" paragraph:

> Phase 3 is complete: the agent mutates files and runs commands behind `PermissionMiddleware`, with atomic
> writes, snapshots/undo, a table-tested risk classifier, and a temporary approval modal. Phase 4 inherits the
> interrupt payload, the pending-approval registry and the rules engine, and must add durable resume, edit-input
> and the allow-rule checkbox without changing the decision semantics. Worktree paths and branch switching are
> recorded on the task; the plan gate (Phase 6) and the verify gate (Phase 7) are not implemented yet.

## Not proposed
- No change to the decisions log (D1–D21), the five axes, phase order, or any other phase's scope.
- No change to `mission.md` or `tech-stack.md`. Phase 3 implements what they already state.
