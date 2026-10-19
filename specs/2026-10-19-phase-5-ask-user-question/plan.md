# Phase 5: AskUserQuestion GenUI. Plan

Status: **Approved on 2026-10-19. All six steps complete; validation passes and the approved constitution completion update is included with final phase changes.**

Implement in order after approval, one commit per completed step. Verify installed packages/source before relying on their APIs. If reality contradicts these requirements, update the spec before product code. Do not change constitution files without approval of exact text.

## Step 1: Verify contracts and define typed question protocol
- Inspect installed deepagents/LangGraph middleware ordering, state and interrupt/resume contracts alongside Phase 4's SQLite proofs. Verify a single mixed pre-tool barrier and an explicit persisted grill readiness transition can be implemented without side effects in replayed nodes.
- Define bounded Pydantic question/options/answers/records and discriminated human-request/answer envelopes with stable call/question IDs. Keep old approval payload compatibility. Specify rank/Other/decline validation and authenticated API error contracts.
- Define `question.asked`/`question.answered`, run mode/interview phase, request-specific waiting metadata and generated TypeScript contracts. Record installed APIs and readiness mechanism in initial learnings; test schemas and a real mixed SQLite interrupt proof.

## Step 2: Implement durable question barrier, storage and API
- Add `ask_user_question` to the actual agent with read-first description. Extend the permission barrier rather than placing a second interrupt inside the tools node.
- Persist independent question and approval resolutions, reconcile checkpoint/event/record ordering, wait for all required answers and return structured tool results exactly once. Add authenticated run-scoped retrieval/resolution and reject mismatched, stale, stopped and duplicate answers.
- Restore pending/partially answered mixed runs through existing provider/vault reconstruction. Preserve graceful shutdown, explicit Stop, event sequence and no-replay effect journals. Apply redaction before every persistence boundary.
- Test all modes, multiple questions/calls, both answer orders, malformed answers, missing dependencies, replay, actual engine kills and canary storage scans. Keep approval-only/configuration action behavior compatible.

## Step 3: Implement grill and exhausted-question consumers
- Persist `/grill` intent and interview/readiness state at run creation and reconstruction. Enforce no mutation/command execution while interviewing; permit reviewed normal implementation only after explicit structured readiness with summary and an answered batch.
- Guide the model through one batch at a time, incorporate answers, preserve task context, handle decline/Stop and continue the original task after readiness. Add deterministic multi-batch Demo and scripted-model proofs; include restart mid-interview and attempts to mutate before readiness.
- Build a typed exhausted-attempts question constructor/result contract and real-engine fixture consumer. Exercise retry/hint, change-approach and stop/report; leave actual fix counters/verify gate to Phase 7.

## Step 4: Build shared QuestionCard and inline question state
- Register QuestionCard in the Zod OpenUI library and regenerate prompt artifacts. Bind controls only to real run/question identities, sharing the component between deterministic and model-composed views.
- Add typed stores/services/hooks for question fetching, replay, answer drafts, validation, navigation, ranking and submission locking; keep business logic out of components.
- Match Main's dock above the composer; add single/multi/rank/Other, complete-batch submission, decline, accessible labels/focus/announcements, fa/en strings, scoped keyboard and responsive logical CSS. Preserve answered/declined history and drafts on failure.
- Add Errors variant using actual context and hint input. Test all types, invalid/failed/duplicate submission, navigation, text/IME safety and forged OpenUI references.

## Step 5: Connect commands, waiting indicators and navigation
- Add `/grill` picker and Home chip with pointer/keyboard insertion; isolate picker shortcuts from task submission and question shortcuts. Preserve literal text, unknown commands and existing hints.
- Extend authoritative question/approval waiting state, background task reopening and Main's minimal current-task summary. Keep approval-only global badge/inbox and existing Rules/branch/worktree/retry behavior.
- Test mixed waiting, partial resolutions, cross-task navigation, replay/restart counts, picker filtering/focus and no horizontal overflow.

## Step 6: Validate Windows behavior and record handoff
- Run every automated and Windows scenario in `validation.md`, including process-kill recovery, Demo/local scripted provider runs, baseline desktop and inspected reference-size fa/en/narrow screenshots.
- Record test evidence, verified installed contracts, deliberate visual extensions and retained limits in learnings; tick only evidenced checks. Preserve secret isolation, permission regressions and later phase scope.
- Propose exact Phase 5 completion row/handoff for constitution approval. After approval, apply and commit with final phase changes; record Phase 6 durable-question integration, Phase 7 exhausted/test-command consumers and Phase 8 grill-me repackaging. Do not start the next phase here.
