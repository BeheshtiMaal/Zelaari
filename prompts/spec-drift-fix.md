# Spec drift prompt (use when code, specs and mock disagree)

Find every place where the implementation, the specs in `specs/`, and the mock in `docs/mock-source/` disagree. The mock is the source of truth for UI; the constitution is the source of truth for behavior unless I say otherwise.
Output a table: item, what each of the three says, your recommendation (change code, change spec, or change mock), and risk. Do not change anything yet. After I approve, apply the agreed changes: update specs first, then code, and add a decision row to `specs/roadmap.md`.
