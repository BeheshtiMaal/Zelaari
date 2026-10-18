"""Optional external Phase 1 credentials. Never load a file from the workspace."""

import os
from pathlib import Path


def load_provider_env() -> None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return
    path = Path(appdata) / "CodeHarness" / "phase1-provider.env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if (
            separator
            and name in {"CODEHARNESS_BASE_URL", "CODEHARNESS_MODEL", "CODEHARNESS_API_KEY"}
            and value
        ):
            os.environ[name] = value.strip("\"'")
