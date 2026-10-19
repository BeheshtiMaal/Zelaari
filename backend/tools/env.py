"""Child environments built from an allowlist. Nothing inherits by accident."""

import os

ALLOWED = {
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "PATH",
    "PATHEXT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "HOMEDRIVE",
    "HOMEPATH",
    "COMSPEC",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "OS",
    "LANG",
    "LC_ALL",
    "TZ",
}

DENIED_PREFIXES = (
    "OPENAI_",
    "ANTHROPIC_",
    "LANGSMITH_",
    "LANGCHAIN_",
    "CODEHARNESS_",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
)

DENIED_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_CREDENTIAL")


def child_environment(secrets: list[str] | None = None) -> dict[str, str]:
    """Allowlist the parent environment, then drop anything that looks like a credential."""
    environment: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper not in ALLOWED:
            continue
        if upper.startswith(DENIED_PREFIXES) or upper.endswith(DENIED_SUFFIXES):
            continue
        environment[key] = value

    # Tracing must stay off even if a host config slipped through the allowlist.
    environment["LANGSMITH_TRACING"] = "false"
    environment["LANGCHAIN_TRACING_V2"] = "false"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"

    for secret in secrets or []:
        if not secret:
            continue
        for key in [key for key, value in environment.items() if secret in value]:
            del environment[key]
    return environment


def redact_environment(environment: dict[str, str], secrets: list[str]) -> dict[str, str]:
    """Belt and braces: strip any value that still contains a registered secret."""
    return {
        key: value
        for key, value in environment.items()
        if not any(secret and secret in value for secret in secrets)
    }
