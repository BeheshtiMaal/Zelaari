"""The eval suite: deterministic cases through the real engine, plus a written live checklist.

Tracing is switched off here, before anything imports the agent stack: these runs happen in
this process rather than under `server/main.py`, which is where the app turns it off. An
eval that phones a tracing backend is slow, noisy, and could carry a task's text off the
machine — the exact thing the product refuses to do.
"""

import os

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
for _key in [key for key in os.environ if key.startswith(("LANGSMITH_", "LANGCHAIN_"))]:
    if _key not in {"LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"}:
        os.environ.pop(_key, None)
