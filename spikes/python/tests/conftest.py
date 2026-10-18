"""Keep experiments independent of credentials and tracing in the host shell."""

import os

# Applied before test modules import LangChain; never inspect or print values.
for variable in list(os.environ):
    if variable.startswith(("LANGSMITH_", "LANGCHAIN_")) or variable.endswith("API_KEY"):
        os.environ.pop(variable, None)
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
