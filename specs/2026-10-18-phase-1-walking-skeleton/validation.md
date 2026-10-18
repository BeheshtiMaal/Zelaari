# Phase 1: Walking Skeleton. Validation

Done only when every box is checked.

## Automated (CI)
- [ ] `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` green.
- [ ] Auth: 401 without or with a wrong token; 200 with the right token.
- [ ] Jail: reading `src/a.txt` works; `../secret.txt`, an absolute outside path, and a symlink/junction pointing outside all return a tool error.
- [ ] Demo run emits ordered events: `run.started -> message.delta* -> tool.call -> tool.result -> message.delta* -> run.finished`, strictly increasing `seq`.
- [ ] SSE reconnect with `Last-Event-ID` resumes with no duplicates and no gaps.
- [ ] Stop during a slow demo stream emits `run.finished{stopped}` in under 1 s.
- [ ] Replay: reducing `events.jsonl` reproduces the live UI state exactly.
- [ ] Canary secret never appears in logs, events, or `events.jsonl`.
- [ ] Engine runs from a plain Python process with no Electron present.

## Manual (Windows 10/11)
- [ ] `npm run desktop` opens the window; input disabled until health passes.
- [ ] Pick a folder, ask "read README.md and summarize" with the demo model: tool line appears, then a rendered OpenUI card (not raw text).
- [ ] The shell matches the mock: dark sidebar with icons, placeholders are visibly disabled, Settings gear at the bottom, chat surface has rounded corners next to the sidebar.
- [ ] Malformed OpenUI Lang falls back to readable text without crashing.
- [ ] First launch opens in Persian (RTL) regardless of Windows language. The English dictionary is checked with a dev flag (`?lang=en`) because the Settings language switch arrives in Phase 2; layout flips correctly with no broken alignment.
- [ ] After normal quit and after force-killing Electron, Task Manager shows no leftover engine process.
- [ ] `netstat -ano` shows the engine bound to 127.0.0.1 only.
- [ ] With a real OpenAI-compatible key set in env vars, the same task works.

## Exit criteria
All boxes checked, `learnings.md` written (Phase 0 spike results, deepagents kwargs actually used), `roadmap.md` updated.
