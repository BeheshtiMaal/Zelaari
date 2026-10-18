# Phase 1 implementation evidence

Implementation approved by the user on 2026-10-18. Phase remains in progress until
every validation check passes. Constitution changes require separate approval.

## Step 0 — verified handoff

Read the entire Phase 0 learnings and installed deepagents 0.7.28 factory source,
the scripted model, Windows job launcher, containment candidate, OpenUI library,
progressive renderer and Electron protocol examples. No blocking contradiction
with the Phase 1 contract was found. Use explicit `TodoListMiddleware`, `app://`,
allowlisted environments with tracing disabled, and a watchdog holding a
kill-on-close job. Bind port zero once and serve the same socket.

OpenUI 1.0.1 uses `defineComponent`, `createLibrary`, `Renderer`, and
`library.prompt()`. The three-component prompt will be generated into a bundled
artifact, rather than hand-maintained in Python. SQLite checkpointing needs its
own package (not installed in the spike environment).

Phase 1 exposes file reads only. Backend operations and tool dispatch must reject
writes and commands independently of the model. The resolve-based jail has the
Phase 0 documented reparse-point race limitation; it is not an OS sandbox.

## Visual direction

Follow Home/Main exactly within Phase 1 scope: frame #1F2125, inset surface
#151618, cards #1E2024, composer #292B31, text #E8EAED, accent #0E7C86.
Bundled Vazirmatn, 240px right sidebar, 24px surface radius, 820px chat column,
Persian first launch and logical CSS. Later-phase controls are disabled.
