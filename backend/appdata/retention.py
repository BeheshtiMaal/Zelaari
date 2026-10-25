"""Run-history retention and clearing.

Only engine storage is ever touched: `.harness/runs/<id>/` and `.harness/checkpoints.sqlite`.
A workspace file is never read, moved or removed here, so "clear history" can never cost
someone their work.
"""

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree

from tools.jail import JailError, storage_path, workspace_root

MAX_RUNS_PER_CALL = 500
"""One call clears at most this many run folders.

The caller repeats until nothing is left. A bound keeps a single request from becoming a
minutes-long disk scan on a workspace with years of history.
"""


def run_directories(root: Path) -> list[Path]:
    """Run folders, newest first, bounded. A missing or unreadable directory is not an error."""
    try:
        directory = storage_path(root, "runs")
        entries = [entry for entry in directory.iterdir() if entry.is_dir()]
    except (JailError, OSError):
        return []
    stamped: list[tuple[float, Path]] = []
    for entry in entries:
        try:
            stamped.append((entry.stat().st_mtime, entry))
        except OSError:
            continue
    stamped.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in stamped[:MAX_RUNS_PER_CALL]]


def directory_size(path: Path) -> int:
    total = 0
    for directory, _, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                total += (Path(directory) / name).stat().st_size
            except OSError:
                continue
    return total


def checkpoint_files(root: Path) -> list[Path]:
    try:
        base = storage_path(root, "checkpoints.sqlite")
    except JailError:
        return []
    # The journal files belong to the same database; deleting the database alone would leave
    # SQLite replaying a journal for a file that no longer exists.
    candidates = [base.with_name(base.name + suffix) for suffix in ("", "-wal", "-shm")]
    return [path for path in candidates if path.exists()]


def run_bytes(root: Path) -> int:
    return sum(directory_size(directory) for directory in run_directories(root))


def prune(root: Path, days: int, now: datetime | None = None) -> int:
    """Delete run folders older than the window. Zero keeps everything."""
    if days <= 0:
        return 0
    moment = now or datetime.now(UTC)
    removed = 0
    for directory in run_directories(root):
        try:
            age = (moment - datetime.fromtimestamp(directory.stat().st_mtime, UTC)).total_seconds()
        except OSError:
            continue
        if age < days * 86400:
            continue
        rmtree(directory, ignore_errors=True)
        removed += 1
    return removed


def prune_workspace(value: str, days: int) -> int:
    """Retention for one workspace by path. A moved or unreadable workspace is skipped."""
    try:
        return prune(workspace_root(value), days)
    except (JailError, OSError, ValueError):
        return 0


def prune_workspaces(workspaces: Iterable[str], days: int) -> int:
    """Startup retention over the recent workspaces."""
    return sum(prune_workspace(value, days) for value in workspaces)


def clear(root: Path) -> tuple[int, int]:
    """Remove every run folder and the checkpoint database. Returns (folders, bytes)."""
    directories = run_directories(root)
    freed = 0
    removed = 0
    for directory in directories:
        freed += directory_size(directory)
        rmtree(directory, ignore_errors=True)
        if not directory.exists():
            removed += 1
    for path in checkpoint_files(root):
        try:
            freed += path.stat().st_size
            path.unlink()
        except OSError:
            continue
    return removed, freed
