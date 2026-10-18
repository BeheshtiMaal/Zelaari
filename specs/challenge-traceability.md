# Challenge Traceability

Source: the challenge brief (build a standalone coding harness, delivered as an installable Windows desktop app).
Every line of the brief maps to a phase and a validation. Nothing in the brief may be left unmapped.

## Expected outputs
| Brief requirement | Where it is delivered | Phase |
|---|---|---|
| Full execution loop: Planning + Execution + Self-Correction | deepagents agent + plan gate + verify gate + reflect budgets | 6, 7 |
| Model connected to file-management and terminal tools | deepagents filesystem tools + `run_command`, behind permission layer | 3 |
| Skill mechanism for new capabilities | `.harness/skills/<name>/SKILL.md`, `load_skill`, install UI | 8 |
| User-confirmation (HITL) for sensitive commands and changes | permission modes, rules grid, approvals inbox | 3, 4 |
| Packaged as an installable Windows desktop app | Electron + PyInstaller sidecar, NSIS installer + portable zip | 10 |

## The five indicators
| Indicator | Concrete behavior we promise | Phase |
|---|---|---|
| 1. Terminal + file access | read/edit/create files, run `pytest`, `pip`/`npm install`, read output | 3 |
| 2. Planning | analyze -> checklist of small steps -> follow it; approval for bigger plans; deviation approval; live thinking/plan/sub-agent timeline | 6 |
| 3. Skills | web search skill, framework-docs skill, custom tool skill (scripts) | 8 |
| 4. Output quality + self-correction | verify gate, test detection, bounded fix loop, quality rules in system prompt + the `python-project` skill | 7 |
| 5. HITL | dangerous terminal commands, edits to protected files, leaving the plan | 3, 4, 6 |

## Cross-cutting
- "Other models can use it easily": provider records (base URL, key, model), connection test, demo model. Phase 2.
- Installer must not require Python or Node on the user's machine. Phase 10.
- Web-search skill is on by default with a per-query approval card. Phase 8.
- Every screen in the UI mock is assigned to a phase in `roadmap.md`.
