# Debug prompt (when a check fails or something behaves wrongly)

Problem: <describe the symptom, the command you ran, and the full error output>.
Rules: reproduce first with a failing test or a minimal script; state 2 or 3 hypotheses ranked by likelihood and how you would falsify each; change one thing at a time; fix the root cause, not the symptom; add a regression test; do not weaken a validation check or a permission rule to make a test pass. If the cause is a wrong spec, stop and tell me. Report: root cause, fix, test added, anything else you noticed.
