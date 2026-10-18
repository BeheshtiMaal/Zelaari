"""Keep tests offline and independent of the host's secrets and tracing."""

import os

for key in list(os.environ):
    if key.startswith(("LANGSMITH_", "LANGCHAIN_", "CODEHARNESS_")) or key.endswith("API_KEY"):
        os.environ.pop(key, None)
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
