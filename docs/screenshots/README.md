# Screenshots

Every PNG in this folder comes from `tests/phase10-screens.ts`, which drives the packaged app
(`dist/win-unpacked/CodeHarness.exe`) — the same tree the installer lays down — in Persian at
the reference size. Nothing here is a drawing of the app: the screens, the tool calls, the
diffs and the refusals are produced by the real engine.

```powershell
npm run desktop:build      # engine bundle + Electron
npm run package            # dist/win-unpacked
npx tsx tests/phase10-screens.ts
```

If your environment injects `NODE_OPTIONS` with a safe-delete shim, run the last line as
`env -u NODE_OPTIONS npx tsx tests/phase10-screens.ts` — the shim blocks the cleanup of the
disposable profile and fails Playwright's teardown.

## How the images were made

- **Window and size.** The window opens at 1440×960 device-independent pixels. This machine
  runs a 133% display scale, so the CSS viewport is 1080×675 and each image is captured with
  `scale: "device"` — a 1440×900 PNG, the size the mocks in `docs/mock-source/` were drawn at.
- **Language.** `CODEHARNESS_LANGUAGE=fa`, so the first paint is Persian and `dir="rtl"`.
- **Profile.** The app runs on a disposable profile at `artifacts/readme-profile` (ignored by
  git), which is why the workspace path in the images reads like a project folder.
- **Model.** `home`, `main`, `run`, `workspace`, `skills`, `schedule`, `schedule-add`,
  `inbox-empty` and the settings screens use the built-in **demo** model: no key, no network.
- **Pending approval.** `inbox` is a real demo run: it reads the file, submits a plan (adopted
  automatically for a single low-risk step), starts it, and asks before the edit. The record
  is left pending on purpose and the run is stopped after the shot.
- **Fixture.** `errors` needs a state a person cannot summon on demand — a model that asks for
  a path outside the workspace — so a local OpenAI-compatible server answers with that one
  tool call. The engine, the permission layer and the jail card are real; only the model is
  scripted. The provider is registered through the engine's own routes (vault key, model
  record, connection test) and the fake server listens on loopback only.
- **No staged DOM.** The script never injects markup, edits styles or fakes an event stream.
  It clicks, types, navigates and reads what the app renders.

## The images

| File | Mock source | What it shows |
| --- | --- | --- |
| `home.png` | `Home.dc.html` | First run: no folder, no model, both empty-state cards |
| `main.png` | `Main.dc.html` | The sample project open, demo model selected, composer ready |
| `run.png` | `Run.dc.html` | A finished demo run: tool line, summary, token meter |
| `workspace.png` | `Workspace.dc.html` | The file browser with a file open |
| `skills.png` | `Skills.dc.html` | Customize › Skills, with the sample's project skill counted |
| `schedule.png` | `Schedule.dc.html` | A weekly schedule with its next run and permission ceiling |
| `schedule-add.png` | `ScheduleAdd.dc.html` | The add-schedule dialog, filled, before saving |
| `inbox-empty.png` | `Empty.dc.html` | The approvals inbox with nothing waiting |
| `inbox.png` | `Inbox.dc.html` | One real pending approval, with the diff and the decision buttons |
| `errors.png` | `Errors.dc.html` | The jail card: a path outside the workspace, refused by the tool layer |
| `settings.png` | `Settings.dc.html` | Settings › Models and keys |
| `settings-add-model.png` | `SettingsAddModel.dc.html` | The add-model dialog: presets, base URL, key, Test |
| `settings-appearance.png` | `SettingsAppearance.dc.html` | Settings › Appearance and language |
| `settings-permissions.png` | `SettingsPermissions.dc.html` | Settings › Permissions and safety |
| `settings-context.png` | `SettingsContext.dc.html` | Settings › Context and compaction |
| `settings-terminal.png` | `SettingsTerminal.dc.html` | Settings › Terminal and tests |
| `settings-data.png` | `SettingsData.dc.html` | Settings › Data and privacy |
| `settings-about.png` | `SettingsAbout.dc.html` | Settings › About |

## Deviations from the mocks

The mock files are design references, not screenshots of the shipped build. Where the build
differs, this is why:

1. **`Empty` is a catalogue, not a route.** `Empty.dc.html` draws the empty states side by
   side. The app renders them where they belong — no folder and no model on the task screen,
   and `inbox-empty.png` for the approvals inbox. `home.png` shows the other two.
2. **`Errors` is one real refusal.** The mock collects the error cards. The screenshot shows
   the one that can be produced deterministically: `jail-card`, from a model asking for a
   path outside the workspace. The timeout and interrupted cards are covered by
   `tests/phase3-desktop.ts`, not by a screenshot.
3. **`Inbox` carries a real diff.** The mock's approval is drawn; this one is a real pending
   record from a demo run, so the file name, the added line and the risk badge are real.
4. **Settings shows seven sections, as drawn**, but the section names come from `src/i18n/fa.ts`
   (`مدل‌ها و کلیدها`, `ظاهر و زبان`, …) rather than the mock's placeholder headings.
5. **SmartScreen is not here.** The "Windows protected your PC → More info → Run anyway"
   dialog belongs to Windows, not to the app, and it only appears for a freshly downloaded,
   unsigned installer. It cannot be produced from a test run; the README describes the two
   clicks in words instead. Capture it once on a clean machine if you want the picture.
6. **The task list in the sidebar is real.** The mock shows invented tasks; the screenshots
   show the one task this walkthrough actually ran, because the profile is fresh.
