# Roadmap proposal

## Current state (post-Phase 3)

- [x] Phase 0: Language spike, Electron bridge, project scaffold.
- [x] Phase 1: Walking skeleton — workspace picker, model picker, task runner, SSE events.
- [x] Phase 2: Conversation history, retry, revert, usage meter, settings.
- [x] Phase 3: Jailed filesystem tools, `run_command`, permission middleware, rules grid, git branch chip,
  worktree option, workspace viewer, approval modal, timeout/jail error cards.

## Proposed

### Phase 4: Persistent approval inbox, call-level retry, rules UI
- Approval inbox (`/approvals`) listing pending + resolved approvals with filters.
- Call-level retry with new arguments (e.g. bump timeout) without a synthetic task string.
- Rules settings surface: mode switch, grid editor, tool × glob → allow/ask/deny.
- Localized approval reasons: engine emits short codes, renderer maps to i18n keys.
- Keyboard shortcuts for common actions (approve with Enter from anywhere, not just modal).
- Desktop test expansion: worktree flow, branch switch, dirty-tree error, timeout card.

### Phase 5: Agent memory and multi-task orchestration
- Summarization of long conversations to stay inside context windows.
- Task dependencies ("run tests after build finishes").
- Scheduled tasks with cron-like recurrence.
- Skill marketplace: install/uninstall skills from the UI.

### Phase 6: Team and security hardening
- Multi-workspace dashboard with cross-project search.
- Secret vault UI (view, rotate, audit) instead of only backend redaction.
- Audit log: every tool call, approval, branch switch, with time and actor.
- Network egress controls: allow-list domains, block all web_search by default in sensitive workspaces.
- Signed updates and integrity checks for the engine bundle.
