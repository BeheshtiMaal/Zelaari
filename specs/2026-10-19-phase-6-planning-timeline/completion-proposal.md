# Proposed Phase 6 constitution update

This is a reviewable proposal, not an applied roadmap change. Apply only after all Phase 6 validation checks pass and the user explicitly approves this exact update. The other constitution files and all later phase rows remain unchanged.

In `specs/roadmap.md`, replace only the Phase 6 row with:

```markdown
| 6 | **Planning + activity timeline - complete** | Structured plans, reviewed initial/deviation gates and workspace settings, stable todo progress, trusted PlanChecklist, scoped reasoning and concurrent read-only delegates, actual summarization notices, truthful telemetry, durable steering and cancellation/recovery. Offline engine and Windows Electron evidence is recorded in `2026-10-19-phase-6-planning-timeline/validation.md` and `learnings.md`. | Run |
```

Insert this handoff before the audit log:

```markdown
## Phase 6 handoff to Phase 7

Phase 6 is complete; validation and installed-runtime contracts are recorded in
`2026-10-19-phase-6-planning-timeline/validation.md` and `learnings.md`. Phase 7 inherits
engine-owned plan/revision/step identities, conservative concrete-file counting,
workspace planning settings behind protected configuration review, and the existing
mixed human barrier. Plan adoption never authorizes an unclassified sibling effect or
bypasses ordinary tool permissions, workspace containment or the effect journal.

Parent turns and read-only reviewer/researcher invocations have durable scoped activity,
provider/model attribution, real reasoning, replayable progress and honest interrupted
states. Completed delegate results survive recovery; uncertain effects are never replayed.
Steering is ordered and idempotent, enters the original parent thread only at a checkpointed
model boundary, and cannot answer a question, grant permission or release a human barrier.
Stop batches terminal activity before deferred ledger cleanup, cancels owned command trees,
and prevents cancelled file replacements. Preserve original provider/vault/worktree identity,
registered-secret redaction, disabled inherited tracing and the documented workspace-jail
race/alias limitations; this remains an application boundary rather than an OS sandbox.

The shared PlanChecklist, step/Thinking/delegate disclosures, right-panel telemetry,
planning settings and editable running composer consume engine events. Latest-request
context occupancy is distinct from cumulative run tokens; estimates and fallback windows
are marked. Summary notices derive from actual installed summarizer transitions. Unavailable
budgets and fix counters are explicit. Phase 7 supplies verification/test detection, bounded
self-correction, enforced budgets and the context-ring/compaction policy; none of those
later-phase features is claimed by Phase 6. Phase 5 question/exhaustion contracts remain
available for its unknown-test-command and retry/change/stop flows.
```

Commit the approved roadmap update together with final Phase 6 validation/handoff evidence. Phase 7 begins only after that completion commit.
