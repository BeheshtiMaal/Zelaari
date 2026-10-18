# Phase 1: Walking Skeleton. Validation

Done only when every box is checked.

## Automated (CI)
- [x] `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` green. Local checks: ruff clean; strict mypy 32 files; pytest 18 passed; TypeScript clean. Windows CI workflow added; no remote CI run claimed.
- [x] Auth: 401 without or with a wrong token; 200 with the right token. `test_auth_and_locked_cors`, `test_plain_python_engine_bound_loopback_and_auth`.
- [x] Jail: reading `src/a.txt` works; `../secret.txt`, an absolute outside path, and a symlink/junction pointing outside all return a tool error. `test_read_and_deny_escapes`, `test_real_symlink_and_junction_escapes`; actual links, no skips. Five forged-tool dispatch cases also pass.
- [x] Demo run emits ordered events: `run.started -> message.delta* -> tool.call -> tool.result -> message.delta* -> run.finished`, strictly increasing `seq`. `test_demo_order_persistence_reconnect_and_secret` asserts real fixture contents; desktop captures 16 ordered events.
- [x] SSE reconnect with `Last-Event-ID` resumes with no duplicates and no gaps. Engine replay test above plus UI `client reconnects a truncated stream with the last applied event id`.
- [x] Stop during a slow demo stream emits `run.finished{stopped}` in under 1 s. `test_stop_is_under_one_second`; terminal bus prevents late events and duplicate finishes.
- [x] Replay: reducing `events.jsonl` reproduces the live UI state exactly. UI `real engine event log replays to identical state through fragmented SSE`; desktop reducer replay checks the actual run's persisted log and visible content.
- [x] Canary secret never appears in logs, events, or `events.jsonl`. Engine canary test also scans SQLite; split-chunk redaction test; desktop checks token absence from events and URLs. Source scan against host credential values clean (zero matches).
- [x] Engine runs from a plain Python process with no Electron present. `test_plain_python_engine_bound_loopback_and_auth`; additionally `scripts/check_packaged.py` completes a real demo read without a Python child.

## Manual (Windows 10/11)
- [x] `npm run desktop` opens the window; input disabled until health passes. Same Electron entrypoint driven by `tests/desktop.ts`; delayed health explicitly checks disabled input. Latest native-window visibility: Persian 0.73 s, English 0.32 s of main-process uptime, under R1's 3 s.
- [x] Pick a folder, ask "read README.md and summarize" with the demo model: tool line appears, then a rendered OpenUI card (not raw text). Desktop test uses a deterministic native-dialog result through real preload IPC; `KeyValue` must show the real `silver-maple` fixture marker. Screenshots inspected.
- [x] The shell matches the mock: dark sidebar with icons, placeholders are visibly disabled, Settings gear at the bottom, chat surface has rounded corners next to the sidebar. Visually inspected `artifacts/home-{fa,en}.png` and `run-{fa,en}.png`; automated sidebar/radius/layout assertions.
- [x] Malformed OpenUI Lang falls back to readable text without crashing. Desktop unknown-component stream fixture; `artifacts/malformed-fa.png`; no renderer exceptions in normal flow.
- [x] First launch opens in Persian (RTL) regardless of Windows language. The English dictionary is checked with a dev flag (`?lang=en`) because the Settings language switch arrives in Phase 2; layout flips correctly with no broken alignment. Fresh Electron profiles for both locales, actual `?lang=en`, direction and sidebar position asserted; screenshots inspected.
- [x] After normal quit and after force-killing Electron, Task Manager shows no leftover engine process. Actual engine/watchdog PIDs checked with psutil, including forced actual main-process termination for both development and packaged engine paths; `artifacts/desktop.json` records passing results. No cleanup is performed before the assertions.
- [x] `netstat -ano` shows the engine bound to 127.0.0.1 only. Desktop invokes `netstat -ano -p tcp`, filters owned engine listeners and asserts loopback only; captured in `artifacts/desktop.json`.
- [x] With a real OpenAI-compatible key set in env vars, the same task works. After the user populated the external provider file and requested a check, `uv run --project backend python scripts/check_live.py` exited 0: real `read_file` tool result contains the `amber-orbit` fixture marker, final response contains OpenUI `Stack` and `Callout`, run finishes completed, and no credential appears in persisted run files or SQLite.

Live check resolved: the earlier AvalAI key returned HTTP 429. The user supplied
alternate configuration through `%APPDATA%/CodeHarness/phase1-provider.env` and
requested validation. The live run passed without printing configuration values
or committing the file. It remains outside the workspace.

## Exit criteria
All boxes checked, `learnings.md` written (Phase 0 spike results, deepagents kwargs actually used), `roadmap.md` updated.

Status: **Phase 1 complete**. Every validation box passes, learnings are recorded,
and the roadmap is updated. Phase 2 is ready for its separate spec approval and
implementation session.
