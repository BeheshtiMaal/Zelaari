# Phase 7: Verify, self-correction, context ring. Requirements

## Goal
The agent proves its work with tests, fixes its own failures in a bounded loop, and the person sees how much of the
context window is in use. Nothing in this phase trusts the model's claim about its own work: the gate, the budgets and the
meter are decided from tool-call results and provider usage.

## In scope
- Test command resolution (detect → project setting → question), pytest and `npm test` only.
- `VerifyGateMiddleware`: no clean finish while files changed and no check has passed since the last change.
- Reflect loop with real limits: fix attempts per step, steps per run, wall time per run.
- `budget.updated` / `budget.exhausted` / `verify.required` / `test.result` events, and the context breakdown.
- `TestResults` and `TerminalPanel` (xterm.js, read-only) on the run screen, including the timeout variant.
- Context ring in the composer toolbar: arc, hover tooltip, click-through breakdown popover, "new chat with summary".
- Compaction driven by the setting (default 60%), emitting `context.summarized`, with the summary persisted for handoff.
- Settings > **Context and compaction** and Settings > **Terminal and tests**, every control functional.
- Token meter fed by `usage.updated`, "~" when estimated.

## Out of scope
Skills and memory loading (Phase 8) — their breakdown rows exist but report 0. Other settings sections, themes, empty
states, schedule, packaging. Runners other than pytest and `npm test` (backlog). Cost or price display (D3). A real OS
sandbox.

## Screens (mock is the source of truth)
`docs/mock-source/Run.dc.html`, `Main.dc.html` (ring and tooltip), `SettingsContext.dc.html`, `SettingsTerminal.dc.html`,
`Errors.dc.html` (fix attempts exhausted, command timeout).

## Functional requirements

**R1 Test detection is a pure, bounded function.**
`detect(root, setting)` returns `{command: str | null, source: "custom" | "pytest.ini" | "pyproject.toml" | "tests" |
"package.json" | "none"}` in this order:
1. `setting.command` (non-empty, trimmed, ≤ 400 chars) → `custom`.
2. `pytest.ini` → `pytest -q`; else `pyproject.toml` that mentions `pytest` (a `[tool.pytest…]` table or a dependency
   string) → `pytest -q`; else a `tests/` directory containing `test_*.py` or `*_test.py` → `pytest -q`.
3. `package.json` with a non-empty `scripts.test` that is not npm's `no test specified` placeholder → `npm test`.
4. Otherwise `none`.
Detection reads only; it never executes a command, never follows symlinks or junctions, skips `.harness/`, `.git/`,
`node_modules/`, and stops after 5 000 directory entries. The source label is what Settings shows ("from pyproject.toml").

**R2 Workspace verification settings exist and are protected.**
`.harness/config.json` gains `context`, `verify` and `terminal` objects, validated by Pydantic models with these defaults
(the mock's values):

| Section | Key | Default | Range |
|---|---|---|---|
| `context` | `compaction_percent` | 60 | 30–90 |
| `context` | `keep_messages` | 8 | 0–50 |
| `context` | `offload` | true | — |
| `context` | `show_ring` | true | — |
| `verify` | `gate` | true | — |
| `verify` | `command` | null (auto) | ≤ 400 chars |
| `verify` | `max_steps` | 40 | 1–200 |
| `verify` | `max_minutes` | 30 | 1–240 |
| `verify` | `fix_attempts` | 3 | 0–10 |
| `terminal` | `shell` | `auto` | auto / powershell / cmd |
| `terminal` | `timeout_seconds` | 120 | 1–600 |
| `terminal` | `max_output_lines` | 200 | 20–2000 |

`GET /verify/settings?workspace=` returns all three objects plus the live detection for that workspace.
`PUT /verify/settings?workspace=` validates the whole document, refuses with 400 without writing anything when invalid,
and goes through the existing protected-configuration approval before the file changes (same path as planning settings).
A missing or corrupt config yields the defaults, never a crash.

**R3 The verify gate blocks an early finish, structurally.**
The gate observes tool results, not text: a mutation is a `write_file` / `edit_file` / `delete` call whose
`ToolMessage.status` is `success`; a verification success is a `run_command` result whose parsed `exit_code` is 0 and whose
normalised command equals the run's resolved verification command. When the model returns a message with no tool calls and
mutations exist that no verification success covers, the gate injects one `[harness]`-prefixed human message naming the
command, emits `verify.required {reason: "unverified_changes", command, injections}`, and routes back to the model instead
of finishing. The gate is off when the `gate` setting is false, the mode is read-only, or no command resolves and the person
declined (R6). It injects at most 3 consecutive times without an intervening successful tool call; then it stops blocking,
emits `budget.exhausted {kind: "verify"}`, and lets the run finish.

**R4 Budgets are enforced and visible.**
One step = one model turn that emits tool calls; the counter, the wall clock (from run start) and the per-step fix
attempts are real. `budget.updated {steps, max_steps, fix_attempts, max_fix_attempts, elapsed_ms, max_seconds}` is emitted
whenever any of them changes. When steps or wall time reach their cap the engine stops the agent, emits
`budget.exhausted {kind: "steps" | "time", limit}` and then `run.finished {status: "stopped"}`; changes stay on disk.
Reaching `fix_attempts` for the current step raises the existing exhausted QuestionCard
(`questions.exhausted.exhausted_question`) on the normal question barrier; the run pauses until it is answered.

**R5 The reflect loop resolves the exhausted card.**
`retry` (with the hint the person wrote) resets that step's attempts, injects the hint and continues. `change` requires a
plan revision through the existing deviation gate and resets the attempts. `stop` lets the model report once with the gate
suspended for that run, then finishes `completed`. A declined exhausted card behaves as `stop`. Answers are validated
against the pending question exactly as in Phase 5.

**R6 An unknown test command is asked once, with a real QuestionCard.**
When the gate must block and no command resolves, it injects one instruction to call `ask_user_question` with header
`Verification` and up to three candidate commands. The gate reads the answered `ask_user_question` tool result (our own
JSON contract) and adopts the chosen option or free text as the run's command. If the card is declined the gate turns off
for that run and emits `verify.required {reason: "declined", command: null, blocked: false}`. The adopted command lives in
memory for that run only; saving it is an explicit Settings action (R2).

**R7 `test.result` is emitted for every verification run.**
`test.result {call_id, command, status: "passed" | "failed" | "error" | "timeout", exit_code: int | null,
passed: int | null, failed: int | null, duration_ms, failures: [str], summary: str}` — `passed`/`failed` parsed from pytest
(`N passed`, `M failed`, `K error`) and from npm-style reporters (`N passing`, `M failing`, `Tests: X failed, Y passed`),
`null` when the output does not say; `failures` holds up to 10 identifiers (`FAILED tests/x.py::y`, `● name`); `summary` is
a bounded (≤ 2 000 chars) redacted excerpt. Parsing is a pure function with its own tests.

**R8 `TerminalPanel` shows command output, read-only.**
xterm.js (`@xterm/xterm` + `@xterm/addon-fit`), no input, no selection of commands, `dir="ltr"`, monospace, `--terminal`
background, header `$ <command>` with the exit code on the other side, body bounded to `max_output_lines` with "show more".
On timeout the header turns red and the body ends with the kill message (`(no output for N seconds)` plus the note that the
process and its children were killed) — the copy from `Errors.dc.html`. Output arrives from `tool.result` for `run_command`
calls and is never interpreted as HTML.

**R9 `TestResults` summarises a run.**
Chips `N passed` (ok tokens) and `M failed` (danger tokens) plus the failing identifiers, from `test.result`; when the
counts are unknown it shows the exit code instead of inventing numbers. Placed directly under the terminal block, as in
`Main.dc.html`.

**R10 The context ring is a small arc with a tooltip.**
22 px arc (`r=14`, `stroke-width=4`, track `#474B54`, progress `#C9D3DD`, round cap, rotated −90°) in the composer toolbar,
no text. Arc fraction = latest `context.updated.input_tokens / context_window`, clamped to 1. Hover and keyboard focus show
a tooltip reading `۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K زمینه استفاده شده` (localised; Persian digits, `٪`, one decimal and `K` above 1 000);
an estimated used value is prefixed `~`, an estimated window is prefixed `~`. Hidden when `context.show_ring` is false or no
`context.updated` has arrived.

**R11 Clicking the ring opens the breakdown popover.**
Radix popover anchored to the ring: rows `messages`, `tool results`, `system and tools`, `active skills`, `memory` with
tokens and a proportional bar, the total (`48.8K / 128.0K`), a marker at the compaction threshold, and a
`new chat with summary` action. Escape closes it and returns focus to the ring; every number is a real measurement
(`~` when approximated).

**R12 The breakdown is measured, not guessed.**
The engine adds `breakdown: {messages, tool_results, system, skills, memory, estimated: true}` to `context.updated`, computed
with `langchain_core.messages.utils.count_tokens_approximately` over the current graph state: non-tool, non-system messages;
`ToolMessage`s; the system message plus tool schemas; skills and memory are 0 until Phase 8 loads them. The same counter the
summarizer uses is the one behind the ring, so the threshold marker and the trigger cannot disagree.

**R13 Compaction follows the setting.**
The summarizer is constructed per run with `trigger=("fraction", compaction_percent / 100)` and
`keep=("messages", keep_messages)`; `offload` decides whether the artifact route under `.harness/context/` is provided.
Every summarisation still emits `context.summarized` (existing contract, unchanged). When offload is on, the redacted summary
text is also written to `.harness/context/summaries/<run_id>.md`.

**R14 "New chat with summary" hands context forward without replaying it.**
`GET /runs/{id}/summary` returns `{summary, run_id, created_at}` or 404 when the run has no summary. `RunRequest` gains
`seed_summary_from: str | null`; when set, the new run's first message is prefixed with a bounded
(`≤ 8 000 chars`, redacted) `Previous conversation summary` block. The popover action is disabled when no summary exists.

**R15 Both settings screens match the mock and work.**
Settings > Context and compaction and Settings > Terminal and tests reproduce the mock's rows, order, copy, controls and
disabled states (exact Persian strings in the appendix). Every control persists through R2 and takes effect on the next run;
the shell row is a real choice, the environment-variables row is a locked information row, and "detected for this project"
shows the live R1 result (`from pyproject.toml` · `pytest -q`) for the selected workspace. "Matches the mock" is verified by
asserting the rendered rows, labels and control values in the Electron suite, not by inspection.

**R16 The token meter is fed by `usage.updated` and honest.**
The run header shows cumulative tokens with `~` when any turn was estimated; the right panel shows context occupancy and the
budget counters (steps, fix attempts) with real numbers instead of the Phase 6 "unavailable" placeholders.

## Wire changes (regenerate `src/lib/protocol.ts`, never hand-edit)
- Promote `test.result` from the reserved `FutureEvent` union to a real event (R7).
- New events: `budget.updated`, `budget.exhausted`, `verify.required`.
- `context.updated` gains optional `breakdown` (R12).
- `RunRequest` gains `seed_summary_from` (R14).
- New models: `VerifySettings` (context/verify/terminal + detection), `RunSummary`.

## Non-functional
- `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` green; UI unit tests via `npm run test:ui`.
- Small typed modules; a test next to every behaviour; no business logic in components.
- No secrets in logs, events, fixtures or the persisted summary (the existing redactor covers both).
- Everything stays inside the workspace jail; detection and the gate never read outside it.
- **Every validation item is automated.** Engine behaviour is proven by `pytest`; formatting, parsing and form mapping by
  `npm run test:ui`; screens, controls, locale, direction and layout by a Playwright-driven Electron suite
  (`tests/phase7-desktop.ts`) that runs the real preload, authenticated loopback engine and SQLite against a disposable
  workspace and profile, with offline scripted models. No check may depend on a person looking at a window; screenshots are
  evidence, never the assertion.

## Decisions (state them in `roadmap.md` when approved)
1. **"Steps" means agent iterations, not plan steps.** The mock shows `گامها ۷ از ۴۰` while the run is at plan step 3 of 4,
   so the counter cannot be plan steps.
2. **Detection order is custom → pytest → npm.** A repo with both runners gets pytest; the Settings screen shows what was
   detected, and a custom command overrides both.
3. **Breakdown numbers are estimates** (provider usage does not split by category); the total still uses provider usage when
   reported, so the ring is exact and the rows are marked `~`.
4. **The unknown-command question is asked by the agent through `ask_user_question`**, because raising a question from a
   middleware outside the tool node would duplicate the Phase 5 barrier. The gate verifies the call happened.
5. **xterm.js is added as a dependency** (`@xterm/xterm`, `@xterm/addon-fit`). If the install is impossible offline, the
   panel falls back to a styled `<pre>` with identical behaviour and the deviation is recorded in `learnings.md`.

## Open questions for the person
1. None blocking. The five decisions above are mine; say the word if any should change.

## Appendix: exact strings from the mock (Persian, RTL)
**Settings > Context and compaction** — title `زمینه و فشرده‌سازی`, intro `مدیریت حافظه‌ی گفتگو و سقف‌های اجرا.`
- Section `پنجره‌ی زمینه`: row `اندازه‌ی پنجره` / `برای هر مدل خودکار تشخیص داده می‌شود (DeepSeek ۱۲۸K، GLM ۲۰۰K)` /
  badge `خودکار`; row `شروع فشرده‌سازی خودکار در` / `وقتی این درصد از پنجره پر شد، پیام‌های قدیمی خلاصه می‌شوند` / value `۶۰٪`
  (range 30–90); row `آخرین پیام‌های کامل` / `چند پیام آخر همیشه بدون خلاصه می‌مانند` / value `۸`; row
  `ذخیره‌ی خروجی بزرگ ابزارها در فایل` / `خروجی طولانی فقط با ارجاع در زمینه می‌ماند` (switch, on); row
  `نمایش حلقه‌ی زمینه در چت` (switch, on).
- Section `سقف‌های اجرا`: `حداکثر گام‌ها` `۴۰`; `حداکثر زمان هر اجرا` `۳۰` + unit `دقیقه`; `تلاش اصلاح برای هر مرحله` /
  `پس از آن از شما می‌پرسد` / `۳`.
- Section `شمارش مصرف` / `فقط توکن؛ اگر تخمینی بود با ~ نشان داده می‌شود` / unit `توکن`.

**Settings > Terminal and tests** — title `ترمینال و آزمون‌ها`, intro `اجرای دستورها و تشخیص آزمون‌ها.`
- Section `ترمینال`: `شل` (select, `PowerShell`); `مهلت هر دستور` `۱۲۰` + `ثانیه`; `حداکثر خطوط خروجی` /
  `بقیه با «نمایش بیشتر» دیده می‌شود` / `۲۰۰`; `متغیرهای محیطی` / `کلیدهای API هرگز به دستورها داده نمی‌شوند` / `قفل · ثابت`.
- Section `آزمون‌ها`: `دستور آزمون` / `تشخیص خودکار: pytest و npm test` / segment `خودکار` | `سفارشی`;
  `تشخیص‌داده‌شده برای این پروژه` / `از pyproject.toml` / `pytest -q`; `دستور سفارشی` /
  `اگر تشخیص ناموفق بود عامل از شما می‌پرسد`; `اجرای آزمون پیش از پایان کار` /
  `اگر فایل تغییر کرده باشد، عامل تا موفقیت آزمون‌ها تمام نمی‌کند` (switch, on).

**Ring and panels** — tooltip `۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K زمینه استفاده شده`; run panel `زمینه` `۳۸٪ · ۴۸٫۸K از ۱۲۸٫۰K`,
`سقف‌ها` / `گام‌ها` `۱۱ از ۴۰` / `تلاش اصلاح این مرحله` `۰ از ۳`; header `~۶۲٬۰۰۰ توکن مصرفی`.
Terminal header `$ pytest -q` + `کد خروج ۱`; chips `۱۱ موفق` / `۱ ناموفق`; timeout card `دستور بعد از ۱۲۰ ثانیه متوقف شد`,
tag `پایان زمان`, body `(بدون خروجی برای ۱۲۰ ثانیه)`, actions `اجرا با مهلت ۳۰۰ ثانیه` / `رد`.
