# Phase 4: Approvals inbox. Verified learnings

Implementation in progress; unchecked validation remains outstanding.

## Installed contracts (Step 1)
- Inspected installed source on 2026-10-19: deepagents 0.7.28, LangGraph 1.2.16, langgraph-checkpoint-sqlite 3.1.2, LangChain 1.4.6.
- `interrupt()` restarts its node. Multiple interrupts inside one task are matched by position, and only the first unanswered one is exposed. The Phase 3 loop cannot expose an entire pending set at once.
- Keep the pre-tool permission barrier, but expose all approvals from that model turn in one graph interrupt envelope. Each decision is independently keyed and validated by tool-call ID; the resume map is keyed by the actual graph interrupt ID. This is not one shared approval for a batch.
- `test_sqlite_interrupt_id_batch_mapping_and_reconstruction` proves the installed SQLite saver restores the exact interrupt ID and accepts reverse-order independent decisions after graph reconstruction.

## Persistence ordering to implement
1. Checkpoint pauses before approval publication; reconstruct missing publications from checkpoint interrupts after a crash.
2. Store approval/decision atomically before emitting its event; reconcile missing events by stable identity after restart.
3. Resume only a fully answered barrier; stable call IDs prevent answer reassignment.
4. Journal side-effect intent before dispatch and its result before returning to the graph. Recovered incomplete intents become interrupted results; never redispatch uncertain effects.
5. Rules proposals bind to a content revision; approval executes exactly that revision or requires refreshed review.

## Scope notes
No constitution changes applied. The approved plan's final roadmap update still needs explicit approval of its exact text.
