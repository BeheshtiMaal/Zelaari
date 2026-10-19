# Phase 2: Models and Workspace. Validation

Status: **Approved by the user on 2026-10-19; validation in progress.**
Done only when every box has passing evidence. Descriptions below are acceptance targets, not claims of existing tests. Never capture real keys in screenshots, traces or artifacts.

## Automated (CI/local Windows)
- [ ] `uv run --project backend ruff check backend`, `uv run --project backend mypy --strict backend`, `uv run --project backend pytest backend/tests`, `npm run typecheck`, `npm run test:ui`, `npm run build`, `npm run build:electron` pass. (R15)
- [ ] Regenerated protocol/GenUI output has no unexplained diff; Python/TS provider IDs, settings/errors and context/usage types agree. (R4, R9)
- [ ] Presets have exactly supplied URLs and null Jev/Metis; exact-host Anthropic inference, lookalike-host rejection and absent price/context/kind inputs tested. (R3–R4)
- [ ] Provider/settings persistence/default survives restart; invalid/unknown/untested/failed providers cannot run/default. URL/model/key edits invalidate success and active runs retain snapshots. (R2–R6)
- [ ] All new endpoints enforce auth/CORS; IPC rejects untrusted frames/malformed payloads; no public response or IPC operation reads stored plaintext keys. (R4–R5, R10–R11)
- [ ] Actual Windows safeStorage encrypt/decrypt works across Electron restart; retention/replacement works; unavailable/decrypt/write failures fail closed; disk contains ciphertext only. (R5)
- [ ] Dynamic canary scan covers success/failure logs, errors/responses, events, app metadata, workspace files and SQLite/checkpoints, including split reasoning/message chunks and credential-echoing exceptions. Test launch arguments/URLs, child environment omission and retired automatic Phase 1 credential-file loading. No real key fixture. (R5, R8)
- [ ] Synthetic HTTP transports exercise OpenAI-compatible and Anthropic adapters with valid/invalid/missing tool-call names/arguments; probe has no filesystem/command effects. (R6)
- [ ] 401/429/no-tools messages/actions tested; at most three total 429 attempts with asserted backoff/retry state, eventual success, exhaustion and cancellation; no nested SDK retries or leaked network errors. (R6)
- [ ] Context tests cover metadata > table > error > 32,768 fallback, wrong model/malformed/nonpositive metadata, unavailable endpoint, provenance persistence and estimated marker; no oversized probes; demo dash. (R7)
- [ ] Native thinking and compatible reasoning_content fixtures produce separate real reasoning deltas; ordinary text is never reasoning; structured/string streams and redaction tested. (R8)
- [ ] Usage tests cover provider input/output, estimates, multi-turn/tool runs, stream/final deduplication, reset and exact replay/reconnect totals. No cost; ring is a placeholder. (R9)
- [ ] Picker and engine independently reject actual drive/UNC roots, home, actual aliases/junctions to forbidden targets, missing folders/files. Valid folders work and cancel preserves selection. (R10)
- [ ] Recents canonical deduplication/restart/stale paths tested; real per-workspace task index restores and replays jailed output without restarting execution. (R10–R11)
- [ ] Branch tests cover ordinary HEAD, gitdir files, detached HEAD and non-git folders, without shell/repository execution. (R11)
- [ ] Settings interaction tests cover seven sections, dialog validation/presets/pending tooltips, key retention, Test/Edit/default, errors/recovery, remembered language, focus trap/return and Escape. (R1–R6, R14)
- [ ] Home tests cover editable chips, prerequisites/demo recovery, workspace/model selection, task navigation, branch, disabled Worktree, recorded mode, placeholder ring, tokens and start/Stop. (R9–R13)
- [ ] Fresh-profile Persian default and persisted English/Persian assert root direction, sidebar side and logical layout properties. (R14)
- [ ] Phase 1 regression suite passes: demo read, auth/loopback, jail escapes, durable ordered SSE/replay/reconnect, Stop under 1 second, OpenUI fallback, tracing isolation and no orphan engine on quit/force-kill. (R4–R5, R10, R12)
- [ ] Desktop integration and bundled-engine smoke checks include JSON resources/adapters and work without a system Python dependency for the bundled engine; record exact commands. (R15)

## Manual (Windows 10/11)
- [ ] Fresh profile opens Persian RTL/dark; no-workspace/no-model panels match Empty mock. Folder picker, Add model and Use demo model recover. Demo works without networking/key. (R2, R10, R13–R14)
- [ ] Inspect screenshots of Home, Models, dialog, language row and provider errors against all six scoped mocks at 1440×900: copy, tokens, spacing, 240px sidebar, rounded surface/backdrop/cards. No fictitious seeded data. (R1–R3, R12–R14)
- [ ] All seven Settings sections visible; only models/language functional. Add/test/edit provider, retain/replace key, default it and restart: persistence/masking correct. Pending presets show URL pending. Keyboard, focus and Escape work. (R1–R6, R14)
- [ ] Persian → English → restart → Persian preserves choice and readable LTR paths/model IDs. Minimum window size has usable controls without clipping. (R14)
- [ ] Native dialog cancel, ordinary folder, drive root, actual home and stale recent folder behave correctly. Workspace list expands real history, persists and opens recorded output without re-execution. (R10–R11)
- [ ] Git branch/detached label/non-git hiding correct. Worktree disabled with Phase 3 explanation. Modes add no execution capability. Chips fill editable text; Home uses chosen workspace/model/mode. (R11–R12)
- [ ] Live OpenAI-compatible provider: add/probe and real jailed read from Home; streamed output, tokens, Stop/replay. Record model, context source and reasoning availability without credentials. (R4, R6–R9, R12)
- [ ] Live native Anthropic provider: add/probe and real jailed read; record model, context source, tokens and whether thinking actually arrived. Synthetic fixtures do not count as live evidence. (R4, R6–R9)
- [ ] Controlled local provider fixture produces 401, repeated 429 and no-tools errors: exact Persian copy/actions, visible retry state/exhaustion, no probe file changes, previous task output intact. (R6)
- [ ] Hover/focus ring and disabled controls; labels make placeholder/deferred status clear. Token estimates show ~ and no monetary value. (R9, R14)
- [ ] Observe vault failure recovery, inspect sanitized canary scan results, and verify no orphan processes after normal and forced desktop exit. (R5, R15)

## Exit criteria
- [ ] Every check has passing evidence; unavailable live/manual checks remain open. `learnings.md` records verified APIs, context table sources, per-provider reasoning matrix, limitations and all deferred TODOs.
- [ ] Approved roadmap update marks phase complete and hands provider IDs, credential service, workspace validation/history, branch metadata, recorded mode and disabled Worktree to Phase 3. No constitution edit without approval.
