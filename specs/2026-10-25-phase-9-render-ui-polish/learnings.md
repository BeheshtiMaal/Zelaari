# Phase 9 implementation evidence

Implementation and validation are complete on settled source; every validation box is ticked in `validation.md` with
named evidence, and the Final evidence table records one sequential run per gate.

## Installed runtime contracts actually used

- **OpenUI, one library, two artefacts.** `src/genui/library.tsx` calls `createLibrary`/`defineComponent` once;
  `library.toJSONSchema()` writes `backend/agent/genui_schema.json` and `library.prompt()` writes
  `backend/agent/genui_prompt.txt`. The Python validator reads the schema, never a hand-written component list, so a
  component that exists in React and not in Python (or the reverse) is impossible. `Stack` and `Tabs` are mutually
  recursive, so they are declared with `z.lazy()`; without it `toJSONSchema()` throws on the cycle.
- **Radix Dialog** already supplied the focus trap, the initial focus, Escape and `aria-modal` for the confirm and
  model dialogs. What it does not supply is focus *restore* to the element that opened the dialog, which is why both
  dialogs carry `onCloseAutoFocus` and remember `document.activeElement` at mount.
- **`contextBridge` copies values.** `baseUrl` and `token` are captured at preload time and cannot be updated from
  the main process afterwards: a getter on the exposed object is evaluated when the object is exposed, not on each
  read, so the "live getter" version of this was dead on arrival and was reverted. A restart therefore hands the
  renderer a new pair through `restart-engine`, and `src/lib/desktop.ts` keeps it in a module-level `live` overlay that
  `connection()` applies. Nothing in `src/` reads `window.harness.baseUrl` directly, which is what makes the overlay
  sufficient; the end-to-end proof is the walkthrough opening the sample workspace after a restart, through the
  renderer's own client on the new port and token.
- **`library.prompt()` is a contract, not documentation.** The model's system prompt and the validator's schema come
  from the same call, so `render_ui`'s instructions and its rules cannot disagree.

## Scripted fixture design

- `backend/providers/genui_demo.py` follows the dispatch-by-task-prefix pattern of Phases 3–7: `demo render` sends one
  valid program, `demo render bad` sends `Chart`, which is not in the library. Both go through the real tool, the real
  validator and the real event bus, so the walkthrough asserts on the product's own path with no key and no network.
- `backend/tests/phase9_seed.py` runs both through `RunManager` and prints the run ids, the component list, the
  one-line refusal (`line 2: unknown component "Chart"`) and the size of `events.jsonl`. It disables LangSmith tracing
  before importing the agent: the seed is offline by design (R19), and the ambient tracing configuration in this
  environment otherwise posts every run to a third party and prints 403s into the log.
- `tests/phase9-desktop.ts` launches the app **three times on one profile**. That is what makes persistence a real
  assertion rather than a state check: the light theme and the large font are set in the first launch, asserted from a
  cold start in the second, and inherited again in the English launch that closes the walkthrough.

## Deviations from the plan, and why

1. **Retention runs in the server lifecycle, not in the catalog.** The plan put the sweep in `store/catalog.py`, but the
   catalog owns settings and knows nothing about when a run starts. `server/app.py` sweeps once at startup and again
   after `POST /runs`, and `appdata/retention.py` stays a pure function over a root and a day count, which is what
   `test_retention.py` can test without a server.
2. **The schedule empty state ships unwired** (Decision 7). The component and its copy are built and covered by
   `states.test.ts`, and `WIRED` in `src/lib/states.ts` records `schedules: null` as the one state no screen reaches
   yet. This is the phase's single recorded deviation from "every empty state is reachable".
   *Closed by Phase 9b:* the Schedule screen exists, `WIRED.noSchedules` is `"schedule"`, and the allowance in
   `states.test.ts` became a requirement that the state is reachable **and** offers its add action. The Phase 9 handoff
   also claimed this state needed no new copy — it did: the help line said "this build has no scheduler", which was
   true then and false now, and the primary action became "Add a schedule".
3. **Five always-ask rows, not three** (Decision 10). The engine locks storage, web, high-risk commands, MCP calls and
   long timeouts; the mock draws the first three. The screen shows what the engine enforces, the mock's three keep
   their order, and the drift is recorded here and in `roadmap.md`.
4. **The engine-condition row's `help` is `null`, not `""`.** The row falls back to the engine's own text when we have
   no sentence of our own, and an empty string is indistinguishable from a forgotten translation — which is exactly
   what `i18n.test.ts` refuses. `null` says "no sentence by design" and the fallback still works.
5. **`shortcuts.ts` replaced two helpers instead of wrapping them.** `questionDigit` and `editableTarget` encoded the
   same rules the new table encodes, so keeping them would have left two implementations to drift. Both were deleted
   and their assertions moved to `shortcuts.test.ts`.
6. **The focus ring is one `:where()` rule.** `:where()` keeps specificity at zero, so a component that genuinely needs
   a different ring can still say so; nine rules with three colours and two offsets became one.

## Defects the final gates exposed

- **Inverse text on a transparent surface (product bug).** The crash card's secondary button carried
  `className="light-button"`, which sets `color: var(--text-inverse)` for its light fill — and then
  `.crash-card button` overrode the fill to `transparent`. In the dark theme that is near-black text on a near-black
  card: the button read as empty. Found by screenshotting the card element rather than the window, fixed by dropping
  the class and giving the rule `color: var(--text)`, and pinned by a new theme test that requires `--text-inverse` to
  appear in the same rule as `--bg-inverse`.
- **Five components were translating themselves.** `locale === "fa" ? "…" : "…"` in the plan checklist, plan review,
  models section, task screen and the interrupted card. `i18n.test.ts` scans `src/components` and `src/app` for
  Persian characters and found all five; the sentences now live in `fa`/`en`, and the scan allows no literal at all.
- **Three `<code>` elements had no direction.** Diff lines, the command picker and the terminal command were inheriting
  the paragraph direction, so a command with a path in Persian text could render backwards. `logical-css.test.ts` now
  requires `dir="ltr"` on every `<code>`.
- **The light palette lost three contrast pairs** when `--focus-ring` was introduced; the ring is now a token with its
  own WCAG pair in both themes rather than borrowing `--accent-bright`.
- **The walkthrough's own assertions were too strict three times**, and each one taught something: the confirm dialog
  has two buttons named "انصراف" (the icon and the text), the About card shows `—` until `appInfo` answers, and the
  demo program renders two callouts because one sits inside a tab panel. These were fixed in the suite, not by
  weakening the product.

## Test-infrastructure limits

- **A cold engine does not fit the sidecar timeout.** A first `import server.app` after a rebuild takes ~44 s in this
  sandbox (AV/disk), against a 30 s sidecar timeout, so `test:desktop` fails with "engine startup timed out" unless the
  interpreter is warmed first (`python -c "import server.app"`, then 4–9 s). The suite is not flaky; the machine is cold.
- **The "one Phase 7 test cannot pass on this machine" claim was wrong, and Phase 9b corrected it.**
  `test_budget.py::test_real_run_raises_the_exhausted_card_and_a_hint_turns_the_check_green` does pass. The failure was
  the invocation: run as `pytest backend/tests` without `uv run`, the venv is not on `PATH`, so the fixture's bare
  `pytest -q` resolved to nothing and every verify result came back "command not found". Through
  `uv run --project backend pytest` — what `npm run test:engine` does — the venv is on `PATH` and the test passes with
  no fixture change at all. The "fix was tried and reverted" note recorded here described a fix for a problem that did
  not exist; `validation.md` carries the correction. The lesson is narrower than "the machine is broken": a gate is
  only a gate if it is run the way the project runs it.
- **The bulk-delete shim trips on build output.** `rm -rf .next out && npm run build` in one command aborts with
  `SAFE_DELETE_BULK_CONFIRM_REQUIRED count=260` when Next unlinks its stale directory, so the removal runs as its own
  command. `pytest` needs `--basetemp` for the same reason.
- **The reference size is emulated.** This display is 1426×798, smaller than the 1440×960 R15 names, so the suite uses
  `page.setViewportSize` rather than resizing a window the screen cannot hold.
- A Node-side render of the timeline is still impossible (`@xterm/xterm` has no Node ESM entry), so every screen-level
  claim in this phase is made in the Electron suite, where the real preload and the real engine run.

## Open items

- The Schedule tab is 9b's screen; the empty state it needs is already built and tested here.
- `render_ui` remains read-only by design (D2): it can draw what a run did, and it cannot create an approval, a
  question or a plan.
