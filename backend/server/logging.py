"""A bounded, redacted engine log.

The engine's stderr goes nowhere on purpose: it can carry provider diagnostics. What a
person can actually send us is this file, so it holds lifecycle events only — never a
task, never a model's reply — is capped, and is scrubbed of anything that looks like a
credential before a byte reaches the disk.
"""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

MAX_BYTES = 512 * 1024
MAX_LINE = 500

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_-]{8,}"), "sk-***"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{8,}=*"), "Bearer ***"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b\s*[:=]\s*\S+"
        ),
        r"\1=***",
    ),
    # A long unbroken hex or base64 run is a session token or a vault blob, not prose.
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "***"),
    (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), "***"),
)


def redact(text: str) -> str:
    """Remove anything that looks like a credential, then bound the length."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    collapsed = " ".join(text.split())
    return collapsed[:MAX_LINE]


def record(message: str, *, now: datetime | None = None) -> str:
    moment = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{moment} {redact(message)}\n"


def open_log(
    directory: Path, *, max_bytes: int = MAX_BYTES, name: str = "engine.log"
) -> Callable[[str], None]:
    """Return `write(message)`. It rotates once at the cap and never raises.

    A full disk or a locked file must not be able to take the engine down, so every
    filesystem failure is swallowed: a missing log line is better than a dead process.
    """
    path = directory / name
    rotated = directory / f"{name}.1"

    def write(message: str) -> None:
        line = record(message)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.stat().st_size + len(line.encode()) > max_bytes:
                if rotated.exists():
                    rotated.unlink()
                path.rename(rotated)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
        except OSError:
            return

    return write
