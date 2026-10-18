# Design tokens (extracted from the UI mock)

The mock source files in `docs/mock-source/*.dc.html` are static design references (inline styles, Persian text). Read them for exact layout and strings.
Do not copy them as production code; rebuild with React, Tailwind v4 and Radix, using these tokens as CSS variables (dark theme default, light theme later).

| Token | Dark value | Use |
|---|---|---|
| `--bg-frame` | `#1F2125` | window background, sidebar |
| `--bg-surface` | `#151618` | inset rounded content surface |
| `--bg-card` | `#1E2024` | cards, panels |
| `--bg-raised` | `#26292F` | chips, inputs on cards |
| `--bg-composer` | `#292B31` (outer `#202226`) | chat box |
| `--bg-active` | `#2E3138` | active nav item, selected segment |
| `--border` | `#2C2F36` (stronger `#33363D`, `#3A3D44`) | borders |
| `--text` | `#E8EAED` | main text |
| `--text-muted` | `#B5BCC5` / `#9AA3AE` / `#7C8590` | secondary text |
| `--accent` | `#0E7C86` (text/ring `#2DD4BF`, tint bg `#12353A`, text `#5EEAD4`) | primary action, selection, progress |
| `--ok` | bg `#12301F`, text `#86EFAC`, solid `#15803D` | success |
| `--warn` | bg `#33290F` / `#2A2415`, text `#FCD34D`, border `#D97706`, badge `#F59E0B` | approvals, caution |
| `--danger` | bg `#3A1A1A`, text `#FCA5A5` / `#F87171`, border `#5C2A2A` | errors, reject |
| `--terminal` | `#0B1118` | terminal and code blocks |
| `--btn-light` | bg `#E4E6EA`, text `#1B1D21` | "New" and "Confirm" buttons |

- **Font:** Vazirmatn (bundled), fallback Tahoma, sans-serif. Mono: Consolas, monospace (always `dir="ltr"` for paths and code).
- **Direction:** `dir="rtl"` on the root; sidebar sits on the right. Use logical properties only (`margin-inline-start`, `inset-inline-end`, `border-inline-end`).
- **Radii:** app surface 24px; composer 26-28px; cards 16-22px; dialogs 28px; chips and pills 20px; inputs 12-14px; buttons 10-12px.
- **Shell:** sidebar 240px; right info panels 288-300px; chat column max 820px centered; dialogs max 620-700px with `rgba(0,0,0,0.62)` backdrop.
- **Digits:** Persian digits (۰-۹) in UI text; code and paths keep Latin.
- **Icons:** 18px stroke icons (Phosphor in production); status dots 8-10px.
