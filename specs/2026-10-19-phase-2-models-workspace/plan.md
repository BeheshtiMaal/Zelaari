# Phase 2: Models and Workspace. Plan

Status: **Approved by the user on 2026-10-19.** Implement top to bottom, one commit per completed step.

Execution: Steps 1–7 are implemented. Step 8 local checks pass with evidence in
`validation.md`; live acceptance remains open at the user's request. The status-only
roadmap amendment is proposed separately and has not been applied without approval.

## Step 1: Verify contracts and define data
- Inspect installed safeStorage, provider adapters, deepagents stream shapes, FastAPI, Radix and static-export APIs; use official docs when local source is insufficient. Record evidence without credentials.
- Define typed provider IDs/records, probe status, context provenance, default/locale settings, workspace/task metadata, error codes and reasoning/usage semantics.
- Define authenticated `GET/POST /models`, `GET/PUT /settings` and narrowly scoped update/test/workspace/task routes and preload operations before implementing consumers. Keep credential handoff separate from public metadata; document exact contracts. Regenerate TS from Python schemas, including arbitrary provider IDs and run mode; update CORS only for required methods.
- Add presets JSON with null pending URLs and a context table of sourced entries only. Add schema/preset/inference tests. If verified APIs contradict the spec, revise the spec first. (R2–R4, R8–R12)

## Step 2: Persist settings and secure credentials
- Add atomic app-data metadata persistence and main-process safeStorage storage with opaque references; persist default/locale.
- Validate IPC payloads/trusted frames. Expose write-only key submission/retention. Synchronize keys into authenticated engine memory on launch/update, registering redaction before provider work; no arguments/environment key transport.
- Fail closed on vault errors, sanitize failures, retire automatic Phase 1 credential-file loading from the product path. Standalone engine tests inject explicit in-memory configuration. Do not import or modify real external credentials.
- Test vault restart, replacement/retention/failure, IPC/auth/CORS and canary absence in files, logs, events and checkpoints. (R2, R4–R5, R14)

## Step 3: Providers, probes and context
- Build verified OpenAI-compatible/native Anthropic adapters and retain keyless demo. Pin any added dependency after verification.
- Implement side-effect-free structured tool probe, capability invalidation/run/default gating, safe errors and three-total-attempt 429 backoff without nested SDK retries.
- Implement models metadata/table/error/fallback context detection with provenance; tolerate absent metadata.
- Test actual adapter HTTP shapes through synthetic transports, malformed/missing tool calls, 401/429, cancellation and context precedence. (R2–R7)

## Step 4: Runs, reasoning and usage
- Replace environment-only selection with provider-ID lookup and per-run snapshots, preserving the jailed read-only agent.
- Add provider-aware reasoning conversion, structured/string bridge extraction and separate secret-safe reasoning/message buffers.
- Accumulate usage once per model turn, add marked estimates and replayable usage/reasoning reducer state; defer Phase 6 timeline.
- Test both adapters plus real deepagents runs, multi-turn usage, deduplication, absent reasoning/usage, split-chunk secrets, replay/reconnect and Stop. (R4–R9)

## Step 5: Workspace selection and history
- Reject forbidden canonical roots/home aliases at picker and engine boundaries; handle cancel/stale folders.
- Persist recents/selection/task index outside workspaces; reopen output by jailed event-log replay without execution. Store no secret-bearing provider/client object in task metadata.
- Read normal/gitdir/detached branch metadata without commands. Add service/store operations for workspace dropdown and expandable task history.
- Test Windows links/junctions, roots/home/UNC, forged paths, recents deduplication/restart/staleness, task replay and git/non-git cases. (R10–R11)

## Step 6: Settings UI
- Rebuild seven-section shell, cards and add/edit dialog from mocks using tokens, Tailwind v4, Radix, Phosphor and logical CSS.
- Wire add/edit/test/save/default, key retention/replacement, detection/probe/retry/errors and accessible pending-preset tooltips.
- Build remembered Appearance language switch and deferred-section states. Test user flows, keyboard/focus and both directions; collect Windows screenshots. (R1–R7, R14)

## Step 7: Home and navigation
- Match greeting, editable quick chips, composer/second bar, model/workspace menus, branch, disabled Worktree, recorded mode and placeholder ring.
- Wire start/Stop, token meter and workspace history through services/stores; add no-workspace/no-model recovery with exact mock copy.
- Keep future skills/context/permission actions explicitly deferred where exposed. Test prerequisites, selection, mode payload, task navigation, usage reset and both locales through real preload. (R9–R14)

## Step 8: Validate and hand off
- Run every automated and manual item in `validation.md`; attach real results/test names and screenshot/observation references. Keep unavailable live-provider checks unticked.
- Write `learnings.md` with verified APIs/versions, context sources, per-provider reasoning matrix, key transport/storage, retry policy, deviations, limitations and all deferred TODOs. Verify bundled engine includes JSON resources/adapters.
- Propose roadmap completion/handoff edit for approval before changing the constitution; mark complete only after all checks pass. Commit approved roadmap amendment with final phase work. (R15)
