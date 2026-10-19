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
