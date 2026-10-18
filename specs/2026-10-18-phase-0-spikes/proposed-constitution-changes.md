# Proposed constitution amendments — approval pending

These are reviewable proposals only. `tech-stack.md` and `roadmap.md` have not been changed.

## 1. Explicit planning middleware (`tech-stack.md`, Engine)

Replace the claim that planning is automatically available with:

> The pinned Phase 0 version is deepagents 0.7.28. It provides filesystem, delegation, and context infrastructure. Planning uses LangChain's `TodoListMiddleware`, passed explicitly to `create_deep_agent` so the offline demo and arbitrary compatible models receive `write_todos` independently of model-specific harness profiles.

In the wiring example, prepend `TodoListMiddleware()` to `middleware=[...]`.
The captured effective system prompt replaces the old authored base prompt; enabled middleware still appends its tool, memory, and skills instructions.

## 2. Windows command backend (`tech-stack.md`, Engine spike notes)

Replace the unresolved shell-backend note with:

> Phase 0 verified that stock `LocalShellBackend` runs cmd and explicitly invoked PowerShell, but its Windows timeout leaves descendants alive and can return later than its requested deadline. Ship a custom command tool and exclude stock `execute` before product command execution. Use a Windows Job Object with kill-on-close ownership and assign processes before resuming them; application lifetime must survive forced Electron termination through a packaged watchdog. The Phase 0 experiment is evidence for this mechanism, not the production permission layer.

Keep custom command implementation in Phase 3 and preserve the Phase 1 requirement that forced Electron termination leaves no engine.

## 3. Provider reasoning (`tech-stack.md`, Providers / Agent activity)

Add:

> Generic `ChatOpenAI` in langchain-openai 1.7.2 discards DeepSeek-style `reasoning_content` in both full responses and streamed deltas. Phase 2 must verify a provider-aware adapter or explicit conversion for this field; the generic adapter alone cannot promise DeepSeek reasoning. Native Anthropic thinking survives langchain-anthropic 1.7.6 as structured `thinking` blocks and normalized `reasoning` content blocks. These are synthetic adapter results; live endpoint validation remains Phase 2 work. Never relabel ordinary answer text as reasoning.

## 4. Sidecar launch and telemetry isolation (`tech-stack.md`, Safety / Engine)

Add:

> Use an OS-bound loopback socket with port 0 rather than probing a free port and rebinding. Hand off the port only after binding. Keep sidecar tokens out of renderer URLs and command arguments. The Windows spike used a temporary launcher environment value, removed before child creation, followed by private stdin pipes to the packaged watchdog and engine. Product Electron should generate its own token. Build child environments from an allowlist and explicitly disable inherited tracing so host development settings cannot enable telemetry in the app.

## 5. Roadmap Phase 0 row

After every validation passes, replace the Phase 0 outcome with:

> Verified spikes — see `2026-10-18-phase-0-spikes/`: both static-export protocols work; recommend `app://`; packaged Windows job/watchdog lifetime verified; deepagents 0.7.28 requires explicit todo middleware for the demo; stock Windows shell unsuitable; demo and reasoning-adapter behavior recorded; containment matrix verified.

Until the real symlink test and remaining validation pass, label the row **validation pending**, and omit the assertion that the complete containment matrix is verified.

Add a Phase 1 handoff note linking the learnings and requiring the explicit middleware, custom app protocol, packaged watchdog lifetime pattern, and disabled inherited tracing. This changes no phase order or product scope.
