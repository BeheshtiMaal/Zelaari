# Roadmap proposal: Phase 3 completion

Approved by the user on 2026-10-19 and applied to `specs/roadmap.md` with the final Phase 3 fixes.

After Phase 3 validation passes, change only the Phase 3 row in specs/roadmap.md to:

| # | Phase | Outcome | Mock screens |
|---|---|---|---|
| 3 | **Tools + permission layer - complete** | Jailed filesystem tools, atomic writes, snapshots and UI undo, process-tree command timeout, rules and modes, risk classifier, temporary approvals, approved branch switching, isolated worktrees, Workspace viewer and timeout/jail cards. Windows Electron evidence and quality gates recorded in 2026-10-19-phase-3-tools-permissions/validation.md. | Workspace (files + tasks) |

Append a handoff note: Phase 4 inherits in-memory temporary approvals and adds the durable inbox, edit/reject flows, allow-rule checkbox and Rules UI. The synthetic timeout retry and English approval reasons remain documented limitations for Phase 4 to consider. No later phase is renamed or reordered; all other constitution text stays unchanged.

Commit the approved roadmap update together with the final Phase 3 work, as required by AGENTS.md.
