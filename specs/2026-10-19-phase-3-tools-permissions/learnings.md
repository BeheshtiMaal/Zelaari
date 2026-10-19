# Phase 3: Tools and permission layer — Verified learnings

## What the source taught us

1. **`interrupt()` must be raised in `aafter_model`, never in `awrap_tool_call`.**
   Interrupt re-executes the raising node from the start. If raised inside `awrap_tool_call`, the graph re-runs the model node, which re-emits all tool calls, causing duplicate writes. Raising it in `aafter_model` (a standalone graph node) isolates the re-execution to the permission layer alone. Verified by reading the installed `HumanInTheLoopMiddleware` source.

2. **Middleware composition order: first in the list = outermost wrapper.**
   LangChain's `_chain_async_tool_call_wrappers` chains in list order. `PermissionMiddleware` is placed first in `build_agent` so it wraps every tool call before any other middleware can touch the filesystem or execute a command.

3. **Per-call interrupts, not per-message.**
   Batching interrupts means a single `Command(resume=...)` applies to every gated call in the message, and a mismatched decision can be silently reused. The middleware stores one `PermissionOutcome` per tool call id, and each call gets its own `interrupt()` so the modal and the resume path are 1:1.

4. **Private graph state must use `PrivateStateAttr`.**
   Without it, the checkpointer serializes the outcomes and the LLM sees them in context on the next turn. `permission_outcomes` is keyed by call id and annotated with `PrivateStateAttr`.

5. **json-schema-to-typescript does not read `prefixItems`.**
   `list[tuple[int, int]]` generates `[unknown, unknown][]`. The client narrows with `changedLineSet(ranges: unknown)` and an explicit shape check.

## Deviations from the plan

6. **`outputFileTracing: false` added to `next.config.ts`.**
   Next.js static export does not ship a server bundle, so tracing is unnecessary. The removal also prevents the WorkBuddy safe-delete shim from timing out when Next unlinks >50 files during "Collecting build traces". The config is correct, not a hack.

7. **`_denial()` missed `write` and `delete` on the first pass.**
   The refactor routing `JailError` through `jail_message` only patched handlers that bound `as error`. `write` and `delete` had a bare `except (...):` with a hardcoded string. A test asserting the shared sentence across every tool caught the gap.

8. **Approval modal's "باز کردن قوانین" button removed.**
   The mock had a link to a rules screen, but no rules UI exists in Phase 3. Instead of linking to `/` (which loses context and is misleading), only the working "جزئیات" toggle is kept. The button returns when Phase 4 adds a rules settings surface.

9. **Engine reason strings are raw English prose in a Persian UI.**
   The reason emitted by `RulesEngine.decide` (e.g. `default write policy in ask mode`) is shown in the modal without localization. The requirement (R21) only says "short reason string", but the visual quality is degraded. Phase 4 should introduce reason codes so the renderer can localize.

10. **Timeout retry is a synthetic task string, not a call-level retry.**
    `retryWithLongerTimeout` starts a new run with the prompt `Run this command again with a timeout of 300 seconds: …`. This satisfies R30's "raises a new approval" but is clunky. A real "retry this call with new arguments" channel belongs in Phase 4.

## Deferred to Phase 4

- Real call-level retry (not a synthetic task).
- Localized approval reasons (reason codes → i18n keys).
- Rules settings UI (`/rules` route backend exists; no frontend surface yet).
- `GET /files` does not support pagination for giant directories.
- The `safe-delete` shim still requires `mv` workaround for large build deletions; the `outputFileTracing` fix covers this project's build only.

## Validation completion repairs (2026-10-19)

- **Framework-level path validation matters.** The backend-only jail tests passed, but an actual graph call to `read_file` with a Windows absolute path was rejected by upstream Deep Agents validation before reaching `WorkspaceBackend`. Its generic error did not match the renderer's jail contract. The outer permission wrapper now resolves filesystem targets before invoking allowed tools and returns `jail_message` for blocked paths. Real graph regressions cover Windows absolute paths and traversal, and confirm the model continues.
- **Branch clicks were bypassing approval.** The route had treated the selection itself as consent, contrary to R24. It now returns an approval payload on `ask`, rechecks the rules on the approved request, and refuses both explicit deny and Read-only. The session hook owns the modal state and displays git stderr on failure; HEAD remains unchanged.
- **Undo existed only as an API.** The Workspace viewer now offers a localized undo button when its selected file has a snapshot. `useUndo` owns snapshot lookup and revert; the viewer refreshes or clears the selected file if undo removes a created file. The desktop fixture checks byte equality, including CRLF content.
- **Error-card styles were missing.** Existence checks alone missed an unstyled jail warning. Both cards now use the mock's tinted panel, border, radius, spacing and monospace command block. Desktop checks assert computed styles as well as text. Windows display scaling can compute a declared 1px border as 0.8px, so the test checks a solid border rather than an exact fractional width.
- **Timeout approvals need the requested limit.** The modal now includes the requested timeout in its reason; otherwise the 300-second retry only mentioned the default 120-second policy. The retry still uses the documented synthetic task approach.
- **Roadmap proposal corrected.** The previous proposal invented later phases conflicting with the constitution. The replacement only marks Phase 3 complete and appends its handoff. The user approved it on 2026-10-19; the completion row and handoff are applied in the final Phase 3 commit under AGENTS.md.
- **Local verification friction.** A cold build and Python imports took minutes with file reads/page-in waits; subsequent checks were fast. The optional Next.js dev browser helper timed out, so the required Electron/static-export path supplied runtime evidence. Next.js 16.4.2 also warns that the existing `outputFileTracing` setting is unrecognized and still collects traces; the earlier claim in item 6 that it disables tracing is not reliable for this installed version. The production build succeeds; that pre-existing configuration is unchanged by these repairs.
