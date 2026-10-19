# Phase 5: Verified learnings

## Step 1 contracts
- User approved requirements/plan/validation on 2026-10-19. Installed versions remain deepagents 0.7.28, LangGraph 1.2.16, langgraph-checkpoint-sqlite 3.1.2, LangChain 1.4.6.
- Phase 4's installed-source verification and executable SQLite proof remain applicable: interrupts re-enter the node; collect independent requests in one envelope before tools, resume using the actual graph interrupt ID. Do not interrupt inside an effectful tools node.
- Question bounds: IDs 128 ASCII identifier characters; headers 40; labels 160; question/description/Other 4000; call and graph IDs 256. Questions/options require distinct IDs and nonblank display text. Rank returns all offered IDs once; Other adds a free-text preference.
- New mixed envelopes use `kind: human`, with separate approvals/questions keyed by call ID. Keep approval-only legacy envelopes unchanged. Question decisions use `kind: question`, the actual graph interrupt ID and per-question selections. Route path retains the call ID as in the approval API. Run-scoped GET `/runs/{id}/questions` returns records, including history. Invalid bodies return 422; unknown run 404; mismatched/stale/duplicate/stopped decisions 409. Missing provider credentials preserve readable records but cannot resume.
- Grill readiness will use a dedicated `finish_interview` structured tool, intercepted by the existing pre-tool middleware and stored in graph state. It requires an answered batch and objective/scope/constraints/acceptance summary; no prose-based transition. Mutation classification remains fail-closed while interviewing, including commands and delegation. Safe project reads and question calls remain available. Readiness cannot authorize sibling effects from its own turn; a subsequent model turn uses normal permissions.
- UI design extends the supplied mock only for undrawn multi/rank/picker states. Local UX guidance confirms full keyboard reachability and visible focus; ranking includes explicit move controls rather than requiring dragging.

## Validation
Record actual test commands and Windows artifacts here as each step completes. Automatic fix-budget detection remains Phase 7, and grill-me skill packaging remains Phase 8.
