"""Atomic file replacement: same-directory temp file, then rename."""

import os
import tempfile
from pathlib import Path


def atomic_write(target: Path, content: str | bytes) -> None:
    """Write through a temp file so a crash never leaves a half-written file."""
    payload = content.encode("utf-8") if isinstance(content, str) else content
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=".harness-tmp-")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
