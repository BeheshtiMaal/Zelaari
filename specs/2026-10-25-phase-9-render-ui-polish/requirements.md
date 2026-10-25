# Phase 9: `render_ui` and polish. Requirements

## Goal
The model can compose UI — and only out of our library, because the library is the prompt and the validator. Every
settings section becomes real, every empty and error state is reachable and says what is safe, and the app gains a
light theme, a font scale, keyboard contracts, ARIA, reduced motion and complete fa/en coverage. Nothing here widens
the permission boundary: `render_ui` writes no file and grants nothing, settings writes keep going through the
Phase 7 protected-configuration approval, and the destructive rows in Data and privacy are the only new irreversible
actions.

## In scope
- `render_ui`: generated library contract, a bounded Python validator, the tool, the event, the renderer path.
- The five missing library components: `TerminalPanel`, `TestResults`, `FileTree`, `Tabs`, `Table`.
- Settings: **appearance and language**, **permissions and safety**, **data and privacy**, **about** (the models,
  context and terminal sections already exist from Phases 2 and 7 and move into the mock's frame unchanged in behaviour).
- Light theme, `system` theme, font scale, a colour/type token sweep.
- The six empty states and the seven error states, including a real engine-crash screen with restart and view log.
- Bounded, redacted log files, because "view log" must open something real.
- Keyboard contracts, focus order, dialog ARIA, reduced motion, RTL/LTR audit.
- fa/en completeness, Persian digits.

## Out of scope
The Schedule tab, the add-schedule dialog and the schedule empty state's *screen* (Phase 9b wires the component this
phase builds). Packaging and the eval suite (Phase 10). Auto-update, code signing, macOS/Linux. New test runners.
A second component tree for light theme. A DOM-level accessibility scanner dependency (axe): the a11y checks assert
roles, names and focus behaviour directly.

## Screens (mock is the source of truth)
`docs/mock-source/SettingsAppearance.dc.html`, `SettingsPermissions.dc.html`, `SettingsData.dc.html`,
`SettingsAbout.dc.html`, `Empty.dc.html`, `Errors.dc.html`. `Settings.dc.html` supplies the shared frame (nav, heading,
section cards, row rhythm). Where a requirement needs something the mock does not draw (the confirm dialogs, the crash
screen's placement, the render_ui failure note), it is specified here and recorded as a decision.

## Functional requirements

**R1 One generated library contract.**
`src/genui/library.tsx` is the only definition of the library. It gains `TerminalPanel(runId, callId)`,
`TestResults(runId, callId)`, `FileTree(runId)`, `Tabs(labels: string[], panels: [...])` and
`Table(columns: string[], rows: string[][])`, and `Stack.children` accepts every component in the library.
`npm run generate:genui` writes two artefacts from it: `backend/agent/genui_prompt.txt` (the prompt the model reads,
already generated today) and `backend/agent/genui_schema.json` (`library.toJSONSchema()`). Both are committed, and
running the generator twice leaves both byte-identical. Engine-state components take ids only; presentational
components take strings, numbers and booleans only, so no component can be told to approve, execute or invent state.
`Tabs` uses two positional arrays of equal length (labels and panels) rather than nested objects: the parser's
sub-component position is an array of refs, which is the shape `Stack` already proves.

**R2 `render_ui` is a read-only tool.**
Tool name `render_ui`, args `{ui: string}` (≤ 20 000 characters). Its description is the generated library prompt plus
a bounded preamble (≤ 8 000 characters total) that says: use only ids that appear in tool results, never repeat the
program in the answer, never put a secret in a string. Category `ui`: `allow` in read-only, ask and auto, and it is
absent from the always-ask list because it changes nothing. It is not a mutation for the Phase 7 verify gate and does
not consume the per-step fix budget. On success the tool result is `{"ok": true, "components": [...], "statements": n}`
(≤ 500 characters), never the program itself.

**R3 Validation is schema-driven, bounded and fails closed.**
`backend/genui/validate.py` validates the program against `genui_schema.json` — not against a second hand-written
component list — so the validator and the prompt cannot drift. Grammar: statements `identifier = expression`; an
expression is a string, number, boolean, `null`, array, object, reference or component call with positional arguments.
Checks: `root` exists and calls the declared root component; every component name is a key of the schema `properties`;
arity is between the required count and the total prop count; each literal matches its declared type (`string`,
`number`, `boolean`, array with an `anyOf` of `$ref`s); every reference resolves; every non-root statement is reachable
from `root`; identifiers are unique and match `^[A-Za-z_][A-Za-z0-9_]{0,63}$`; nesting depth ≤ 8; ≤ 200 statements.
Id-typed props (`runId`, `callId`, `approvalId`, `planId`) additionally match `^[A-Za-z0-9_-]{1,64}$`. The first
failure becomes one line, ≤ 200 characters, with the 1-based line number (`line 3: unknown component "Chart"`). Any
exception inside the validator becomes that same error shape; the tool never raises.

**R4 Failure is visible and recoverable, success is evidence.**
Both outcomes emit one event `ui.render {call_id, ok, text, components, statements, error}` and are appended to
`runs/<id>/events.jsonl`, so a replayed run reconstructs exactly the UI that was shown. On failure the tool result is
the short error (R3) and the run continues — the model may fix the program or answer in markdown; the timeline shows the
model's markdown plus an inline note carrying the error, so a silent fallback never hides a broken program. On success
the timeline renders the program with the existing `Renderer`, and a render-time error (zod, unknown prop) still falls
back to the escaped text with `data-testid="fallback"`. The UI text passes through the existing redactor before it is
persisted.

**R5 The model cannot render outside the library.**
A program naming a component that is not in the schema is rejected before rendering, with no partial render. An id the
run never produced renders the component's own "not found" state and creates nothing: `ApprovalCard`, `QuestionCard` and
`PlanChecklist` read engine state by id and cannot approve, answer or set progress. `DiffView`, `Table`, `Tabs`,
`Stack`, `Callout`, `KeyValue` are display-only. `FileTree` lists the files the run actually changed (derived from the
persisted action journal), not a path list the model supplied. Tests assert each of these.

**R6 The Settings frame matches the mock.**
`src/components/settings/settings-frame.tsx` owns the 200px nav (title `تنظیمات`, seven sections, the active one on
`--bg-active` with `aria-current="page"`), the heading (h2 + one-line intro) and the content column
(`flex:1; min-width:380px; max-width:840px`, 14px gap, section cards `--bg-card` with `--border` and 18px radius,
20px horizontal padding, rows separated by a 1px top border). `settings-screen.tsx` becomes the frame plus one
component per section (`models`, `appearance`, `permissions`, `context`, `terminal`, `data`, `about`). Each section has
`data-testid="settings-section-<slug>"` and each nav button `settings-nav-<slug>`. Behaviour of the models, context and
terminal sections is unchanged.

**R7 Appearance and language is functional.**
Rows: interface language (فارسی / English), theme (تیره / روشن / مثل سیستم), font size (کوچک / متوسط / بزرگ), then an
`فعالیت عامل` card with three switches — show the thinking panel, keep the current step's thinking open, show terminal
output inside the chat. Language, theme and font size apply immediately and are stored in app `Settings` (no approval:
they are preferences). The three activity switches are also app preferences and take effect on the next rendered
timeline; turning the thinking panel off removes the disclosure entirely and never relabels an answer as reasoning;
turning terminal-in-chat off collapses command output to a one-line summary that can be expanded, so output is never
lost. Defaults match the mock: fa, dark, medium, all three switches on.

**R8 Permissions and safety is functional.**
Four cards. **Default mode**: read-only / ask / auto, stored in app `Settings.default_mode`; a new task starts in it and
the composer still overrides per task. **Plan approval**: a switch for the gate, the step threshold (default ۴) and the
file threshold (default ۳) — these three are the existing workspace planning settings, read from
`GET /planning/settings` and written through `PUT /planning/settings` (protected approval), so the screen shows the
pending review instead of a success state. **Always ask, even in Auto**: read-only rows with the mock's `قفل · ثابت`
chip, rendered from the engine's `RulesResponse.always_ask` list — never editable, and the screen fails closed (every
known condition shown as locked) if the list cannot be read. The mock draws three of these (rules and system files, web
search, high-risk commands); the engine reports five (those three plus MCP tool calls and timeouts above the default).
The screen shows what the engine enforces, so the mock's three appear first and the other two follow (Decision 10).
**Tool and folder rules**:
the effective grid from `GET /rules` (tool, scope, decision badge `مجاز`/`بپرس`/`ممنوع`) plus a link to
Customize → Rules and permissions for editing. Without a workspace the section explains that rules are per workspace
and offers the folder picker.

**R9 Data and privacy is functional.**
**Where data lives**: the real app-data path (monospace, `dir="ltr"`) with an `باز کردن` button (IPC `reveal-app-data`,
which only ever opens the app-data root), the workspace `.harness/` label, and a retention select (۷ / ۳۰ / ۹۰ روز /
همیشه) stored in app `Settings.retention_days`; the engine applies it on startup and after a run by deleting run folders
older than the window and never a workspace file. **Privacy**: a `صفر` chip for data sent to us, and the web-search
switch, which is the Phase 8 per-workspace skill enable (direct write, no approval). **Danger zone**: clear all run
history and delete all vault keys. Each opens a confirm dialog that names exactly what is removed (run count and path,
or key count), requires an explicit `می‌دانم` checkbox, and offers the destructive button only then. Clearing run
history is `DELETE /data/runs` (run folders, `.harness/checkpoints.sqlite`, task rows — never workspace files);
deleting keys is IPC `clear-keys` (safeStorage) plus `DELETE /internal/credentials`. Both write one audit line to the
bounded log with counts only.

**R10 About is honest.**
Version from Electron `app.getVersion()` (IPC `app-info`), and a test asserts it equals `package.json`'s version and the
engine's reported version. Rows: version `0.1.0`, licence `MIT`, built with `Electron، deepagents، OpenUI`, updates
(`خودکار نیست؛ نسخه‌ی جدید را دستی نصب کنید`) with a `بررسی دستی` button that re-reads the running version and reports
"you are running 0.1.0; this build has no update channel" — no invented URL, no network call. A `ایمنی و محدودیت‌ها`
card carries the mock's honest sentence (`این برنامه ماشین مجازی یا sandbox واقعی نیست؛ حفاظت‌ها در لایه‌ی ابزار و
تأیید انسانی هستند`) with the `SECURITY.md` chip, and `باز کردن پوشه‌ی لاگ` (IPC `open-log-folder`).

**R11 The six empty states are reachable and actionable.**
One `EmptyState` primitive (`src/components/states/empty-state.tsx`) with icon, title, help, one or two actions and
optional suggestion chips, matching the mock's centred layout (56px circle, 16px title, 13.5px help, ≤ 320px text).
States: no workspace, no model, empty approvals inbox, no schedules, workspace with no tasks, no skills enabled.
Every action does something real: `انتخاب پوشه` opens the picker, `پروژه‌ی نمونه` materialises the bundled
`examples/sample-project` into app data on first use and selects it (`POST /workspaces/sample`), the workspace's
suggestion chips fill the composer, `مرور مهارت‌ها` opens Customize → Skills. The no-schedules state is built and
unit-tested here and wired to a surface in Phase 9b; that is the one deviation from "every one reachable", recorded in
`learnings.md`.

**R12 The seven error states are reachable, and the crash screen is real.**
Model 401, 429 (automatic backoff), model without tool calling, command timeout, jail block, fix attempts exhausted and
**engine crash**. The first six exist from Phases 2, 3, 5 and 7 and keep their copy and controls; they are re-asserted.
New: when the sidecar exits unexpectedly the app no longer destroys its windows — the renderer shows a blocking card
(`موتور عامل ناگهان بسته شد`, the mock's "your work is saved, nothing runs half-finished" sentence) with
`راه‌اندازی دوباره` and `مشاهده‌ی لاگ`. Restart is IPC `restart-engine`: close the old sidecar, start a new one,
re-register the vault credentials, return the new connection, and the renderer re-runs its bootstrap; the open task is
then reopened from its persisted events and its interrupted state is honest (no replay of an uncertain effect).
Every error card keeps the mock's three-part shape: what happened, what is still safe, what to do.

**R13 Theme and type scale cover every token.**
`:root` is the dark palette; `[data-theme="light"]` defines the same token names with a derived light palette;
`system` resolves to one of the two from `prefers-color-scheme` and follows changes. The theme is applied to
`<html>` before first paint, so there is no flash of the wrong palette. A token sweep removes every colour literal
outside the two palette blocks (242 today) and every raw `font-size: Npx` outside the type-scale block (142 today), so
a rule can only use a token. The font scale is a `--fs-*` step set overridden by `[data-font="small"|"medium"|"large"]`
on `<html>` (base 13 / 14 / 16px); `zoom` is not used because xterm measures its own cell size. Body text keeps ≥ 4.5:1
contrast and borders ≥ 3:1 against their surface in both themes, computed from the tokens by a test.

**R14 Keyboard, focus and ARIA are contracts, not accidents.**
One table in `src/lib/shortcuts.ts` (pure, tested) documents: composer Enter sends / Shift+Enter adds a line / `/` and
`@` open their pickers / Esc dismisses them; question cards 1–4 pick an option, Enter advances, Esc declines; approvals
Enter approves, Esc rejects, and the inbox list moves with Arrow keys; Esc closes any dialog. Dialogs are Radix Dialog
with a labelled title, `aria-modal`, initial focus inside, a focus trap, Escape to close and focus restored to the
trigger. The shell has a skip link to `main`, exactly one visible focus-ring style, and no positive `tabindex`.
`prefers-reduced-motion: reduce` removes transitions, animations and the streaming caret. Live regions: the timeline is
`aria-live="polite"`, status lines are `role="status"`, failures are `role="alert"`.

**R15 RTL and LTR hold in both directions.**
No physical CSS property anywhere: a test scans `src/app/globals.css` and every TSX inline style for
`margin-left|margin-right|padding-left|padding-right|border-left|border-right|left:|right:|text-align: left|right` and
fails. `dir` and `lang` follow the locale on `<html>`; mixed content uses `dir="auto"` or `bdi`; code, commands and paths
stay `dir="ltr"`. The Electron suite switches to English and asserts the sidebar moves to the left, the composer
mirrors, and no element overflows horizontally at 1440×960.

**R16 Every string is in both dictionaries, and Persian UI uses Persian digits.**
Every user-visible string — section intros, row labels, empty and error copy, aria labels, titles, confirm dialogs —
comes from `fa`/`en`, which are typed against each other. A test asserts identical key sets and shapes, no empty
strings, identical `{placeholder}` sets per key, no Persian characters in `en`, and no ASCII digits in `fa` copy. A
second test scans `src/components/**` and `src/app/**` for Persian literals and allows exactly one exception, the
language name `فارسی`. Numbers are formatted with `Intl.NumberFormat(locale)`; counts, durations and thresholds show
Persian digits in Persian (versions, paths and code stay Latin, per `docs/design-tokens.md`).

**R17 Wire and events.**
New event `ui.render`. New/changed models: `GenUiRender`, `Settings.default_mode`, `Settings.appearance`
(`theme`, `font`, `show_thinking`, `keep_thinking_open`, `show_terminal`), `Settings.retention_days`,
`DataSummary` (app data path, workspace `.harness` path, run count, oldest run, retention), `AppInfo` (version,
electron, engine, licence), `SampleWorkspace`. New routes: `DELETE /data/runs`, `POST /workspaces/sample`,
`GET /data`, `GET /about`. New IPC: `app-info`, `restart-engine`, `engine-status`, `open-log-folder`,
`reveal-app-data`, `clear-keys`. `src/lib/protocol.ts` is regenerated, never hand-edited.

**R18 Quality gates.**
`ruff`, `mypy --strict backend`, `pytest backend/tests`, `tsc --noEmit`, `npm run test:ui`, `npm run build`,
`npm run build:electron`, `npm run test:desktop`, `tests/phase9-desktop.ts` and the Phase 2–8 desktop baselines are
green, and `npm run generate:protocol` plus `npm run generate:genui` are idempotent. Every validation item is
automated; no check depends on a person looking at a window.

**R19 Boundaries and privacy.**
`render_ui` grants nothing, writes nothing and cannot create an approval, a question or a plan. The validator is
bounded in input size, statements, depth and identifier shape, and never evaluates anything. Logs are the only new
files: `<app data>/logs/engine.log` and `main.log`, each ≤ 512 KB with one rotation, written through the existing
redactor, with no prompt text, no key and no command output; the crash screen shows no token. Retention and the danger
zone touch only run folders, the checkpoint database and the vault — never a workspace file. No new network traffic.

## Resolved questions (answered before implementation)
1. **Phase 8 committed first.** Done: `ef4a296 feat(phase8): skills, connectors and the Customize hub`, 105 files, on
   top of the Phase 7 docs commit. Phase 9 starts from a clean tree.
2. **The schedule empty state ships now** (Decision 7): the component and its copy are built and unit-tested in this
   phase, and 9b wires them to the Schedule tab. This is the one recorded deviation from "every empty state is
   reachable".
3. **Default theme is dark** (Decision 9), with `system` as an option, matching the mock and the Persian-first default.
4. **All five always-ask rows are rendered** (Decision 10): the mock's three first, then MCP tool calls and timeouts
   above the default. The screen shows what the engine enforces; the two extra rows are recorded as mock drift in the
   audit log.

## Decisions (also recorded in `roadmap.md`)
1. **The generated JSON schema is the validator's contract.** One source of truth (`library.tsx`), two artefacts
   (prompt, schema), no hand-maintained component list in Python.
2. **`render_ui` is read-only**, so it never asks: it changes no file, no rule and no permission. A tool that asked on
   every render would train the person to click approve.
3. **Light theme is a palette, not a second tree.** The same components render in both themes because every colour is a
   token; the sweep is a precondition, so it lands before the light palette.
4. **The font scale uses type tokens, not `zoom`**, because xterm measures its own cell size and `zoom` breaks it.
5. **The crash screen keeps the app alive.** Today a sidecar exit destroys the windows and quits; from this phase the
   renderer gets a status and an explicit restart, which is the only way "restart" can exist.
6. **`بررسی دستی` reports the running version.** This build has no update channel and no repository URL is recorded in
   the project, so the button never opens an invented URL.
7. **The schedule empty state ships as a component, wired in 9b**, because the Schedule tab is 9b's screen.
8. **Destructive rows use two confirmations** (a dialog that names the effect, then an explicit checkbox), not an
   approval in the inbox: they are the person's own action on their own app data, and an inbox approval would make the
   person approve themselves.
9. **A fresh install is dark.** The mock is dark, the product is Persian-first, and the OS preference is one click away
   under `مثل سیستم`; following the OS by default would make the first screen depend on a machine setting the person
   never chose here.
10. **The always-ask list shows the engine's five, not the mock's three.** The mock is the source of truth for layout,
    not for the safety model: showing three would tell the person that MCP calls and long timeouts run unattended in
    Auto, which they do not. The mock's three keep their order at the top, the extra two follow, and the drift is
    recorded in the audit log.

## Appendix: exact strings from the mock (Persian, RTL)
**Appearance**: intro `زبان، تم و نمایش فعالیت عامل.`; cards `نمایش` / `فعالیت عامل`; rows `زبان رابط`
(`پیش‌فرض: فارسی (راست‌به‌چپ)`), `تم` (`تیره پیش‌فرض است`), `اندازه‌ی قلم`; segments `فارسی` `English`,
`تیره` `روشن` `مثل سیستم`, `کوچک` `متوسط` `بزرگ`; switches `نمایش پنل تفکر` (`فقط وقتی مدل استدلال ارسال کند`),
`باز بودن تفکر مرحله‌ی جاری` (`بعد از پایان مرحله خودکار جمع می‌شود`), `نمایش خروجی ترمینال داخل چت`.
**Permissions**: intro `تعیین کنید عامل چه چیزی را بدون پرسیدن انجام دهد.`; cards `حالت پیش‌فرض` / `تأیید برنامه` /
`همیشه بپرس، حتی در حالت خودکار` / `قوانین ابزار و پوشه`; rows `حالت هر گفتگوی جدید` (`می‌توانید در هر کار عوضش کنید`),
`برای کارهای بزرگ تأیید برنامه بخواه` (`کارهای کوچک بدون توقف اجرا می‌شوند`), `حداقل تعداد مراحل` (`برنامه‌ی ۴ مرحله یا
بیشتر`), `بیش از چند فایل` (`تعداد فایل‌های مورد انتظار`), `تأیید خروج از برنامه` (`فایل خارج از محدوده یا تغییر مراحل`),
`قوانین و فایل‌های سیستمی` (`.harness/rules.json و پوشه‌ی .harness`), `جست‌وجوی وب` (`هر کوئری قبل از ارسال نمایش داده
می‌شود`), `دستورهای پرخطر` (`حذف بازگشتی، فرمت دیسک، نصب بسته، push اجباری`); chip `قفل · ثابت`; badges `مجاز`
`بپرس` `ممنوع`.
**Data**: intro `داده‌ها فقط روی این دستگاه می‌مانند.`; cards `محل ذخیره` / `حریم خصوصی` / `منطقه‌ی خطر`; rows
`داده‌ی برنامه`, `داخل پوشه‌ی پروژه` (`قوانین، حافظه، مهارت‌ها و تاریخچه‌ی اجرا`), `نگه داشتن تاریخچه‌ی اجراها`,
`ارسال داده به ما` (`هیچ؛ فقط گفتگو با مدل انتخابی شما و جست‌وجوی وب (با تأیید)`), `مهارت جست‌وجوی وب`
(`هر کوئری قبل از ارسال تأیید می‌خواهد`), `پاک کردن تاریخچه‌ی همه‌ی اجراها` (`برگشت‌پذیر نیست`),
`حذف همه‌ی کلیدها از گاوصندوق Windows` (`باید دوباره وارد کنید`); buttons `باز کردن` `پاک کردن` `حذف کلیدها`; chip `صفر`.
**About**: intro `نسخه و محدودیت‌ها.`; cards `CodeHarness` / `ایمنی و محدودیت‌ها`; rows `نسخه`, `مجوز` (MIT),
`ساخته‌شده با` (`Electron، deepagents، OpenUI`), `به‌روزرسانی` (`خودکار نیست؛ نسخه‌ی جدید را دستی نصب کنید`),
`ایزوله‌سازی` (`این برنامه ماشین مجازی یا sandbox واقعی نیست؛ حفاظت‌ها در لایه‌ی ابزار و تأیید انسانی هستند`),
`گزارش‌ها` (`برای عیب‌یابی`); buttons `بررسی دستی` `باز کردن پوشه‌ی لاگ`; chips `MIT` `SECURITY.md`.
**Empty**: no workspace `هنوز پوشه‌ی پروژه‌ای انتخاب نکرده‌اید` / `یک پوشه انتخاب کنید تا عامل فقط داخل همان کار کند.
بیرون از آن هیچ فایلی خوانده یا نوشته نمی‌شود.` (`انتخاب پوشه` `پروژه‌ی نمونه`); no model `هنوز مدلی اضافه نشده` /
`کلید API یک مدل را اضافه کنید، یا با مدل نمایشی بدون کلید و اینترنت شروع کنید.` (`افزودن مدل` `مدل نمایشی`);
inbox `همه‌چیز مرتب است` / `چیزی منتظر تأیید شما نیست. هر درخواست حساس عامل اینجا نشان داده می‌شود.`;
schedules `کار زمان‌بندی‌شده‌ای نیست` / `کارهای تکراری مثل اجرای شبانه‌ی تست‌ها را اینجا تنظیم کنید.` (`کار جدید` `الگوها`);
no tasks `در این فضا هنوز کاری نیست` / `یک کار بنویسید یا از پیشنهادها شروع کنید.` (chips `رفع باگ` `نوشتن تست`
`توضیح پروژه`); no skills `مهارتی در این فضا فعال نیست` / `عامل فقط با ابزارهای پایه کار می‌کند. مهارت‌ها را از
سفارشی‌سازی روشن کنید.` (`مرور مهارت‌ها`).
**Errors**: crash `موتور عامل ناگهان بسته شد` / `کار شما ذخیره است و بعد از راه‌اندازی دوباره از آخرین نقطه ادامه
می‌یابد. هیچ فرمانی نیمه‌کاره اجرا نمی‌شود.` (`راه‌اندازی دوباره` `مشاهده‌ی لاگ`).
