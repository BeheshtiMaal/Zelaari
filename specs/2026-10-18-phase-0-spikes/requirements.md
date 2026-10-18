# Phase 0: Spikes. Requirements

## Goal
De-risk the Windows desktop stack with isolated, disposable experiments before product implementation. Deliver reproducible evidence and verified API notes, not product features.

## In scope
- Experiments, fixtures, tests, and dependency locks under `spikes/` only.
- Next.js 16 static export in Electron, OpenUI rendering, packaged FastAPI sidecar lifecycle, deepagents integration, scripted demo model, provider reasoning transport, and Windows path containment.
- Evidence and findings in this phase folder, using `learnings.md` as the canonical output. This resolves the brief's undated `specs/phase-0-spikes/learnings.md` reference in favor of the constitution's dated phase layout.
- `Home.dc.html` and design tokens as context for rendering requirements; no screen implementation or visual acceptance target in Phase 0.

## Out of scope
Product UI, settings, persistence, installer, real provider credentials, live paid model calls, and production permission middleware. No changes to product folders or constitution without separate approval.

## Functional requirements
- **R1 — Isolation and reproducibility:** Keep all executable experiments under `spikes/`. Record Windows, Python 3.12, Node, package manager, and exact resolved dependency versions. Commit dependency locks and commands that reproduce each experiment. Verify APIs against installed source/signatures or official documentation; record sources and versions without assuming API shapes.
- **R2 — Static UI and OpenUI:** Build a Next.js 16 static export with React 19 and test both Electron `file://` and custom `app://` loading. Define a Zod component library containing `Callout`, `Stack`, and `KeyValue` using the specified OpenUI packages. Verify prompt generation, progressive rendering from chunked OpenUI Lang, final output, and readable malformed-input fallback without a crash. Record the result of each protocol and recommend at least one working route.
- **R3 — Sidecar handshake and authentication:** Package a minimal FastAPI app using PyInstaller onedir and launch it from Electron. Bind only to `127.0.0.1` using an OS-assigned free port; the first stdout line is exactly a JSON port announcement (`{"port":N}`). Deliver a fresh bearer token privately in memory at launch, never through arguments, URLs, logs, or workspace files. Health requests with absent/wrong tokens return 401; the launch token returns 200. Repeat launches prove fresh tokens and successful port allocation.
- **R4 — Sidecar lifecycle:** Prove that normal Electron quit and forced termination of the Electron main process leave no sidecar or spawned descendant alive. Record the Windows lifecycle mechanism used, process IDs, cleanup deadline (at most 5 seconds), and how failure/timeout cleanup works. Test a descendant process so killing just the immediate child cannot produce a false pass.
- **R5 — deepagents APIs and activity:** Pin deepagents and verify `create_deep_agent` parameters for backend, skills, memory, subagents, middleware, checkpointer, and interrupt handling. Record how to fully replace its default system prompt and verify the effective prompt in a captured model request. Exercise `write_todos`, `task`, and interrupt/resume; record actual stream envelopes, relevant activity fields, and decision payloads. Use in-memory checkpointing for this experiment; production persistence is out of scope.
- **R6 — Windows shell:** Exercise the installed stock local shell backend with PowerShell and cmd, including output, nonzero exit, timeout, and a command spawning a child. Record shell selection, timeout semantics, and whether descendants survive. Unsupported behavior is a valid finding only with a reproducible test and an explicit workaround recommendation; a stock-shell deficiency must not be reported as a passing safety guarantee.
- **R7 — Scripted demo model:** Implement an offline deterministic chat model that binds tools with `create_deep_agent`, streams text, emits a tool call, receives its result, and finishes. Assert chunk ordering and tool execution through a real deepagents invocation without network access or credentials.
- **R8 — Provider reasoning:** Feed synthetic DeepSeek-style `reasoning_content` and Anthropic thinking blocks through the actual installed provider adapters, including streaming chunk conversion. Record what survives, exact access paths, adapter configuration, and unsupported cases. Test that ordinary assistant text is never labeled reasoning and missing reasoning is distinguishable. These checks establish adapter behavior, not live-provider compatibility.
- **R9 — Windows containment:** Test a resolve-and-contain candidate with allowed relative files and blocked escapes: `..`, absolute outside paths, sibling-prefix collisions, symlinks, junctions, drive-relative paths, UNC paths, and mixed case/separators. Define explicit rejection for ambiguous drive-relative and UNC inputs in this candidate. Exercise both existing targets and a not-yet-existing file under an escaping linked parent. Use temporary fixtures; never access real network shares. If symlink creation lacks privileges, record it as an outstanding validation rather than silently skipping it. Document residual limitations such as path races; this experiment is not a production jail.
- **R10 — Evidence and handoff:** Write `learnings.md` with pinned versions, verified signatures/API shapes, runnable snippets, test evidence, failures/workarounds, and proposed constitution changes. Label every experiment supported/unsupported/unresolved. Every unresolved item has its impact and next action; no untracked TODOs. Do not edit the constitution to adopt a recommendation before approval.

## Non-functional requirements
- Python is typed and passes ruff, strict mypy, and pytest; TypeScript is strict and passes `tsc --noEmit`. Checks cover the spike source rather than creating an empty product `backend/` solely for `mypy --strict backend`.
- Tests validate actual behavior; every automated validation below maps to a real test. No tests require external accounts, keys, or network services at runtime.
- No secrets in code, logs, fixtures, reports, or workspace files. Runtime tokens remain ephemeral; secret-leak tests use generated canaries held in memory and assert only redacted results.
- Commit each implementation plan step separately. The current workspace has no `.git`; initialize a local repository in implementation Step 1 if still absent. Do not configure a remote or publish anything.

## Decisions requiring later approval
- Any constitution edits discovered by the experiments are proposals in `learnings.md` first. Phase completion must not silently change the roadmap.
- Jev/Metis URLs and the web-search backend remain unresolved and outside this phase; no invented endpoints are needed for these offline experiments.
