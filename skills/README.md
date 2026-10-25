# Bundled skills

Each folder is a skill: `SKILL.md` with `name`, `description` and an optional `command`.
The model only ever sees the name and the description; the body is loaded on demand by
`load_skill`, and only when the person enabled the skill for that workspace.

| Folder | Command | Category | Why it exists |
|---|---|---|---|
| `grill-me` | `/grill` | coding | Interview before building; drives the Phase 5 question barrier |
| `feature-spec` | `/spec` | coding | Requirements, plan and validation before implementation |
| `fix-failing-tests` | `/fix` | tests | The bounded run → read → hypothesise → fix loop |
| `python-project` | — | coding | Layout, typing, pytest and ruff conventions |
| `web-search` | `/search` | web | Current facts; every query needs approval |

`examples/sample-project/.harness/skills/read-framework-docs/` is the example **project**
skill: it ships with that project, is off by default, and is the shape a team copies.

Adding a skill here makes it available to every workspace as `source: bundled`. Bundled
skills cannot be edited or deleted from the hub; install your own copy instead.
