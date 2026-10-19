# Phase 2: Models and Workspace. Validation

Status: **Complete on 2026-10-19: all checks pass, including the user-approved roadmap completion update. Phase 3 has not started.**
Done only when every box has passing evidence. Checked items have observed passing evidence; unchecked items remain acceptance targets. Never capture real keys in screenshots, traces or artifacts.

## Automated (CI/local Windows)
- [x] `uv run --project backend ruff check backend`, `uv run --project backend mypy --strict backend`, `uv run --project backend pytest backend/tests`, `npm run typecheck`, `npm run test:ui`, `npm run build`, `npm run build:electron` pass. (R15)
  Evidence: 40 engine tests and 8 UI unit tests passed; ruff, strict mypy (48 files), TypeScript, production export and Electron build passed.
- [x] Regenerated protocol/GenUI output has no unexplained diff; Python/TS provider IDs, settings/errors and context/usage types agree. (R4, R9)
  Evidence: Protocol and GenUI regeneration produced no semantic diff; test_model_contracts and test_event_roundtrip_and_schema.
- [x] Presets have exactly supplied URLs and null Jev/Metis; exact-host Anthropic inference, lookalike-host rejection and absent price/context/kind inputs tested. (R3–R4)
  Evidence: test_presets_and_inference, test_model_contract_and_arbitrary_run_id; desktop asserts four dialog inputs and disabled pending presets.
- [x] Provider/settings persistence/default survives restart; invalid/unknown/untested/failed providers cannot run/default. URL/model/key edits invalidate success and active runs retain snapshots. (R2–R6)
  Evidence: test_catalog_persistence_and_memory_only_keys, test_active_run_keeps_model_and_key_snapshot, rotation test and native restart/default/failed-model denial checks.
- [x] All new endpoints enforce auth/CORS; IPC rejects untrusted frames/malformed payloads; no public response or IPC operation reads stored plaintext keys. (R4–R5, R10–R11)
  Evidence: test_all_new_routes_require_auth_and_put_cors_is_locked, test_model_auth_validation_and_write_only_credentials; IPC frame/payload unit tests.
- [x] Actual Windows safeStorage encrypt/decrypt works across Electron restart; retention/replacement works; unavailable/decrypt/write failures fail closed; disk contains ciphertext only. (R5)
  Evidence: Actual DPAPI save, retain, replace, restart and unavailable-encryption flow in tests/phase2-desktop.ts; vault unit tests cover encrypt/decrypt/write failures.
- [x] Dynamic canary scan covers success/failure logs, errors/responses, events, app metadata, workspace files and SQLite/checkpoints, including split reasoning/message chunks and credential-echoing exceptions. Test launch arguments/URLs, child environment omission and retired automatic Phase 1 credential-file loading. No real key fixture. (R5, R8)
  Evidence: Native canary scan covers all persisted app-data/workspace files, including SQLite, after success and echoed-secret errors; split stream test and child-environment unit test pass. Desktop imports no Phase 1 provider loader.
- [x] Synthetic HTTP transports exercise OpenAI-compatible and Anthropic adapters with valid/invalid/missing tool-call names/arguments; probe has no filesystem/command effects. (R6)
  Evidence: test_actual_compatible_probe_transport and test_native_anthropic_http_probe_and_thinking_stream use real SDKs with synthetic HTTP transports; draft probe leaves catalog empty.
- [x] 401/429/no-tools messages/actions tested; at most three total 429 attempts with asserted backoff/retry state, eventual success, exhaustion and cancellation; no nested SDK retries or leaked network errors. (R6)
  Evidence: Compatible transport tests assert request count, backoff and retry state; cancellation test passes. Native fixture counts exactly three 429 requests.
- [x] Context tests cover metadata > table > error > 32,768 fallback, wrong model/malformed/nonpositive metadata, unavailable endpoint, provenance persistence and estimated marker; no oversized probes; demo dash. (R7)
  Evidence: test_context_precedence_and_validation covers metadata/table/error/fallback; native metadata field verified locally. Desktop shows matching 65,536 metadata context and fallback markers.
- [x] Native thinking and compatible reasoning_content fixtures produce separate real reasoning deltas; ordinary text is never reasoning; structured/string streams and redaction tested. (R8)
  Evidence: Native thinking present/absent HTTP fixtures and compatible conversion/round-trip tests; native desktop run emits redacted reasoning.delta without answer mixing.
- [x] Usage tests cover provider input/output, estimates, multi-turn/tool runs, stream/final deduplication, reset and exact replay/reconnect totals. No cost; ring is a placeholder. (R9)
  Evidence: test_meter_uses_final_usage_once_and_marks_any_estimate, reducer replay test, native two-turn run/replay both show 240 tokens; demo uses a marked estimate.
- [x] Picker and engine independently reject actual drive/UNC roots, home, actual aliases/junctions to forbidden targets, missing folders/files. Valid folders work and cancel preserves selection. (R10)
  Evidence: test_selection_safety_recents_and_git_metadata and native validator unit test exercise actual home, drive, localhost UNC-root refusal and Windows home junctions; native dialog cancellation/refusal tests pass.
- [x] Recents canonical deduplication/restart/stale paths tested; real per-workspace task index restores and replays jailed output without restarting execution. (R10–R11)
  Evidence: Workspace tests cover stale paths/deduplication; test_completed_task_restores_and_replays_without_execution and native restart/history replay assert no extra model request.
- [x] Branch tests cover ordinary HEAD, gitdir files, detached HEAD and non-git folders, without shell/repository execution. (R11)
  Evidence: Workspace metadata test covers normal HEAD, gitdir, detached HEAD and non-git; implementation reads metadata only.
- [x] Settings interaction tests cover seven sections, dialog validation/presets/pending tooltips, key retention, Test/Edit/default, errors/recovery, remembered language, focus trap/return and Escape. (R1–R6, R14)
  Evidence: Native Settings flow covers all seven sections, deferred panels, presets, key retention/replacement, defaults/errors, locale persistence and keyboard focus/escape/return at 800 x 600.
- [x] Home tests cover editable chips, prerequisites/demo recovery, workspace/model selection, task navigation, branch, disabled Worktree, recorded mode, placeholder ring, tokens and start/Stop. (R9–R13)
  Evidence: tests/phase2-desktop.ts covers chips, prerequisites, selection, mode payload, disabled Worktree/ring tooltips, branch/task list and usage; tests/desktop.ts covers demo start and completed Stop state; test_stop_is_under_one_second covers active cancellation.
- [x] Fresh-profile Persian default and persisted English/Persian assert root direction, sidebar side and logical layout properties. (R14)
  Evidence: Fresh native profile defaults to fa/RTL, persisted en restores LTR; both native suites assert direction. Logical CSS declaration unit test passes.
- [x] Phase 1 regression suite passes: demo read, auth/loopback, jail escapes, durable ordered SSE/replay/reconnect, Stop under 1 second, OpenUI fallback, tracing isolation and no orphan engine on quit/force-kill. (R4–R5, R10, R12)
  Evidence: Full engine regression suite and tests/desktop.ts pass; native timing 0.274 s Persian / 0.299 s English, auth/loopback/netstat and normal/forced cleanup verified.
- [x] Desktop integration and bundled-engine smoke checks include JSON resources/adapters and work without a system Python dependency for the bundled engine; record exact commands. (R15)
  Evidence: npm run build:engine passed; scripts/check_packaged.py passed authenticated presets/models/settings and real demo read without a Python child. Both provider JSON resources are bundled.

## Manual (Windows 10/11)
- [x] Fresh profile opens Persian RTL/dark; no-workspace/no-model panels match Empty mock. Folder picker, Add model and Use demo model recover. Demo works without networking/key. (R2, R10, R13–R14)
  Evidence: Native first-launch/deterministic-dialog flow and offline demo; inspected artifacts/phase2/home-empty-fa.png against Empty reference.
- [x] Inspect screenshots of Home, Models, dialog, language row and provider errors against all six scoped mocks at 1440×900: copy, tokens, spacing, 240px sidebar, rounded surface/backdrop/cards. No fictitious seeded data. (R1–R3, R12–R14)
  Evidence: Inspected home, models, dialog, appearance, run and error captures under artifacts/phase2; icons/inner empty-state panels follow the mock. Deferred controls follow the approved scope restrictions.
- [x] All seven Settings sections visible; only models/language functional. Add/test/edit provider, retain/replace key, default it and restart: persistence/masking correct. Pending presets show URL pending. Keyboard, focus and Escape work. (R1–R6, R14)
  Evidence: Native all-section walk, real safeStorage save/edit/default/restart, accessible URL pending tips and keyboard checks; models-fa.png and dialog-fa.png inspected.
- [x] Persian → English → restart → Persian preserves choice and readable LTR paths/model IDs. Minimum window size has usable controls without clipping. (R14)
  Evidence: Native remembered English restart then Persian/English switching; 800 x 600 RTL/LTR and modal screenshots inspected, with no horizontal overflow.
- [x] Native dialog cancel, ordinary folder, drive root, actual home and stale recent folder behave correctly. Workspace list expands real history, persists and opens recorded output without re-execution. (R10–R11)
  Evidence: Native controlled folder-dialog results exercise cancellation/root/home/valid selection; real Windows junction tests cover aliases. Stale paths and history are tested independently; no interactive filesystem dialog claim is made.
- [x] Git branch/detached label/non-git hiding correct. Worktree disabled with Phase 3 explanation. Modes add no execution capability. Chips fill editable text; Home uses chosen workspace/model/mode. (R11–R12)
  Evidence: Native phase-two branch display/mode payload/disabled Worktree/chip fill; gitdir/detached/non-git cases verified with filesystem fixtures.
- [x] Live OpenAI-compatible provider: add/probe and real jailed read from Home; streamed output, tokens, Stop/replay. Record model, context source and reasoning availability without credentials. (R4, R6–R9, R12)
  Evidence (2026-10-19): `npx tsx tests/phase2-live-desktop.ts` passed actual Electron dialog add/probe/save/default, Home jailed read, streamed output, measured token display, safeStorage restart, identical persisted replay and Home Stop for gpt-4o-mini and claude-haiku-4-5 through the supplied AvalAI compatible URL. Context: metadata 128,000 / 200,000; input/output usage: 14,405/233 and 6,194/132; no reasoning emitted. Stop: 90 ms / 332 ms. Scan: 76 persisted files without plaintext key; zero renderer errors. Evidence/screenshots: `artifacts/phase2-live/`.
- [x] Live native Anthropic provider: add/probe and real jailed read; record model, context source, tokens and whether thinking actually arrived. Synthetic fixtures do not count as live evidence. (R4, R6–R9)
  Evidence (2026-10-19): `backend/.venv/Scripts/python.exe scripts/check_live.py --native-adapter --model claude-haiku-4-5` passed live catalog add, tiny tool probe and real jailed read through the actual Anthropic Messages SDK against AvalAI; streamed OpenUI, measured usage 6,779 input / 191 output, identical replay, Stop and persisted-key scan passed. Context fallback 32,768 estimated; no thinking emitted. This is an explicit memory-only diagnostic adapter override, not a native gateway UI routing claim. Separately, live Claude add/probe/Home via the supplied compatible URL passed as above; exact-host product inference remains unchanged.
- [x] Controlled local provider fixture produces 401, repeated 429 and no-tools errors: exact Persian copy/actions, visible retry state/exhaustion, no probe file changes, previous task output intact. (R6)
  Evidence: Local provider fixture emits 401/429/no-tools; both error locales inspected. API denies failed providers for defaults/runs, retains prior output, and makes exactly three rate-limit attempts.
- [x] Hover/focus ring and disabled controls; labels make placeholder/deferred status clear. Token estimates show ~ and no monetary value. (R9, R14)
  Evidence: Native focus-driven tooltips assert Phase 3 Worktree and Phase 7 ring help; demo meter estimate and 240-token provider meter observed. No cost fields.
- [x] Observe vault failure recovery, inspect sanitized canary scan results, and verify no orphan processes after normal and forced desktop exit. (R5, R15)
  Evidence: Actual safeStorage unavailability fails closed; native canary scan found no full key in persisted files; regression desktop verifies normal/forced process cleanup.

## Exit criteria
- [x] Every automated and manual check has passing evidence. `learnings.md` records verified APIs, context table sources, per-provider reasoning matrix, limitations and all deferred TODOs.
- [x] Approved roadmap update marks phase complete and hands provider IDs, credential service, workspace validation/history, branch metadata, recorded mode and disabled Worktree to Phase 3. No constitution edit without approval.
  Evidence: user explicitly approved the completion proposal on 2026-10-19; `specs/roadmap.md` now marks Phase 2 complete and records the approved handoff. Provider inference, phase scope and order are unchanged.
