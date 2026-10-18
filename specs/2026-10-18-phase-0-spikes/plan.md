# Phase 0: Spikes. Plan

Work top to bottom after explicit approval of this spec. Commit after each step; do not start Phase 1.

## Step 1: Prepare isolated experiments (R1)
- Initialize a local Git repository if still absent; preserve existing files and record the approved specs in the initial baseline.
- Create `spikes/` with isolated Python and Next/Electron projects, strict tooling, fixture/test layout, and a command guide. Ignore dependency directories, builds, and local runtime artifacts.
- Verify available toolchains and install compatible dependencies using official metadata; pin exact resolved versions and commit locks. Record verification sources in a draft `learnings.md`.

## Step 2: Static export and OpenUI (R2)
- Verify the installed library-definition, prompt-generation, and rendering APIs.
- Build the three-component library and deterministic chunk stream, with malformed-input fallback.
- Exercise the static export through both Electron protocols. Add browser/Electron assertions for component output, incremental rendering, fallback, asset loading, and renderer errors. Record the recommended protocol and any failures.

## Step 3: Packaged sidecar and cleanup (R3, R4)
- Implement minimal loopback/authenticated health service and a race-free port handshake, then package onedir.
- Implement the isolated Electron launcher and Windows process-tree lifetime mechanism, including forced parent termination.
- Add packaged integration tests for handshake, bind address, auth, fresh launches, startup failure cleanup, normal quit, force kill, descendant cleanup, and token leakage. Ensure test cleanup runs even on failure.

## Step 4: deepagents, demo model, and Windows shell (R5, R6, R7)
- Capture installed signatures, effective system prompt, middleware/skills/memory/backend wiring, checkpointer configuration, and interrupt/resume payloads using disposable fixtures.
- Implement the deterministic offline model and exercise streamed text, tool binding/execution, todos, subagent activity, and resume decisions through real agent runs.
- Exercise stock shell behavior under PowerShell and cmd with successful, failing, timed-out, and child-spawning commands. Clean up any surviving fixture processes; record unsupported behavior and a concrete alternative for later phases.

## Step 5: Reasoning transport (R8)
- Build synthetic streaming and non-streaming provider responses and feed them through installed OpenAI/Anthropic adapters using mocked HTTP transport.
- Assert retained reasoning fields, separation from text, and missing-reasoning behavior. Record limitations and exact configurations without implying live service verification.

## Step 6: Windows containment (R9)
- Implement the disposable resolve-and-contain candidate and temporary filesystem fixtures.
- Test the full path matrix, symlink/junction targets, and missing write targets under linked parents. Record privilege prerequisites and remaining limitations; remove only test-owned fixtures using native filesystem operations.

## Step 7: Validate and document handoff (R10)
- Run all automated checks and manually exercise every item in `validation.md`; tick only items with concrete evidence.
- Finalize this folder's `learnings.md` with versions, APIs, snippets, outcomes, commands, and proposed spec changes.
- Prepare any necessary roadmap/tech-stack amendments for user approval. After approval, apply and commit them with the relevant spike artifacts. If approval is pending, report that completion is pending rather than marking the phase done.
- Summarize results, deviations, unresolved questions, and the Phase 1 handoff. No product code in this phase.
