"""Pre-mutation snapshots and revert. Also the diff source for agent-changed lines."""

from __future__ import annotations

import difflib
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from store.secrets import Redactor
from tools.atomic import atomic_write
from tools.jail import Resolved, resolve, storage_path
from tools.types import RevertResult, SnapshotMeta

MAX_SNAPSHOT_BYTES = 20_000_000
"""A single file larger than the whole store budget cannot be undone; the mutation is refused."""

MAX_ENTRIES = 200
MAX_TOTAL_BYTES = 20_000_000


class SnapshotError(RuntimeError):
    """Raised when the pre-mutation state cannot be captured, so the mutation must not happen."""


def _new_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}-{uuid4().hex[:6]}"


class SnapshotStore:
    """`.harness/snapshots/<id>/{meta.json,content.bin}`."""

    def __init__(
        self,
        root: Path,
        *,
        run_id: str | None = None,
        max_entries: int = MAX_ENTRIES,
        max_bytes: int = MAX_TOTAL_BYTES,
        redactor: Redactor | None = None,
    ) -> None:
        self.root = root
        self.run_id = run_id
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.redactor = redactor

    def _check_credentials(self, payload: bytes) -> None:
        if self.redactor and any(
            secret.encode(encoding) in payload
            for secret in self.redactor.values
            for encoding in ("utf-8", "utf-16-le", "utf-16-be")
        ):
            raise SnapshotError("Snapshot would contain a protected credential; action refused")

    @property
    def directory(self) -> Path:
        return storage_path(self.root, "snapshots")

    def _entry(self, snapshot_id: str) -> Path:
        if not snapshot_id or any(mark in snapshot_id for mark in ("/", "\\", "..")):
            raise SnapshotError("Invalid snapshot id")
        return storage_path(self.root, f"snapshots/{snapshot_id}")

    def _artifact(self, snapshot_id: str, name: str) -> Path:
        self._entry(snapshot_id)
        return storage_path(self.root, f"snapshots/{snapshot_id}/{name}")

    # -- write -------------------------------------------------------------
    def capture(self, target: Resolved, *, tool: str, call_id: str | None = None) -> str:
        """Record the current state of `target` before it changes."""
        existed = target.path.is_file()
        payload = b""
        if existed:
            size = target.path.stat().st_size
            if size > MAX_SNAPSHOT_BYTES:
                raise SnapshotError(
                    f"File is {size} bytes; the undo limit is {MAX_SNAPSHOT_BYTES} bytes"
                )
            payload = target.path.read_bytes()
        self._check_credentials(payload)

        snapshot_id = _new_id()
        directory = self._entry(snapshot_id)
        try:
            directory.mkdir(parents=True, exist_ok=False)
            if existed:
                (directory / "content.bin").write_bytes(payload)
            meta = SnapshotMeta(
                id=snapshot_id,
                path=target.relative,
                existed=existed,
                ts=datetime.now(UTC).isoformat(),
                run_id=self.run_id,
                call_id=call_id,
                bytes=len(payload),
                tool=tool,
            )
            (directory / "meta.json").write_text(meta.model_dump_json(), encoding="utf-8")
        except OSError as error:
            shutil.rmtree(directory, ignore_errors=True)
            raise SnapshotError(f"Could not record the previous state: {error.strerror}") from error
        self.prune(keep=snapshot_id)
        return snapshot_id

    # -- read --------------------------------------------------------------
    def meta(self, snapshot_id: str) -> SnapshotMeta:
        try:
            path = self._artifact(snapshot_id, "meta.json")
            meta = SnapshotMeta.model_validate_json(path.read_text(encoding="utf-8"))
            resolve(
                self.root,
                meta.path,
                allow_protected=(
                    meta.path.replace("\\", "/").casefold() == ".harness/rules.json"
                    and meta.tool == "rules_update"
                ),
            )
            return meta
        except (OSError, ValueError) as error:
            raise SnapshotError("Unknown or unreadable snapshot") from error

    def content(self, snapshot_id: str) -> bytes | None:
        meta = self.meta(snapshot_id)
        if not meta.existed:
            return None
        payload = self._artifact(snapshot_id, "content.bin").read_bytes()
        self._check_credentials(payload)
        return payload

    def entries(self) -> list[SnapshotMeta]:
        """Newest first."""
        if not self.directory.is_dir():
            return []
        entries: list[SnapshotMeta] = []
        for child in sorted(self.directory.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            try:
                entries.append(self.meta(child.name))
            except SnapshotError:
                continue
        return entries

    def newest_for(self, relative: str) -> SnapshotMeta | None:
        for entry in self.entries():
            if entry.path == relative:
                return entry
        return None

    def changed_lines(self, relative: str, current: str | None = None) -> list[tuple[int, int]]:
        """Inclusive 1-based ranges of the current file that differ from the newest snapshot."""
        newest = self.newest_for(relative)
        if newest is None:
            return []
        if current is None:
            try:
                current = (self.root / relative).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return []
        if not newest.existed:
            count = len(current.splitlines())
            return [(1, count)] if count else []
        try:
            previous = self._artifact(newest.id, "content.bin").read_bytes().decode("utf-8")
        except (OSError, ValueError):
            return []
        if previous == current:
            return []
        ranges: list[tuple[int, int]] = []
        matcher = difflib.SequenceMatcher(
            a=previous.splitlines(), b=current.splitlines(), autojunk=False
        )
        for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
            if tag in {"insert", "replace"} and j2 > j1:
                ranges.append((j1 + 1, j2))
        return ranges

    # -- revert ------------------------------------------------------------
    def revert(self, snapshot_id: str) -> RevertResult:
        meta = self.meta(snapshot_id)
        if meta.path.replace("\\", "/").casefold() == ".harness/rules.json":
            raise SnapshotError("Rules restoration requires an approval proposal")
        target = resolve(self.root, meta.path)
        if target.path.is_dir():
            raise SnapshotError("Snapshot target is a directory")

        # Record what is being replaced, so a revert is itself revertible.
        try:
            previous = (
                self._artifact(snapshot_id, "content.bin").read_bytes() if meta.existed else b""
            )
        except (OSError, ValueError) as error:
            raise SnapshotError("Snapshot contents are unavailable") from error
        self._check_credentials(previous)
        restored = self.capture(target, tool="revert", call_id=None)

        try:
            if meta.existed:
                atomic_write(target.path, previous)
            else:
                target.path.unlink(missing_ok=True)
        except (OSError, UnicodeError) as error:
            raise SnapshotError(f"Could not revert: {error}") from error
        return RevertResult(path=meta.path, snapshot_id=snapshot_id, created_snapshot_id=restored)

    # -- retention ---------------------------------------------------------
    def prune(self, keep: str | None = None) -> None:
        """Drop the oldest entries beyond the count or byte budget, never `keep`."""
        kept = 0
        total = 0
        for entry in self.entries():  # newest first
            within_count = kept < self.max_entries
            within_bytes = total + entry.bytes <= self.max_bytes
            if entry.id == keep or (within_count and (within_bytes or kept == 0)):
                kept += 1
                total += entry.bytes
                continue
            shutil.rmtree(self._entry(entry.id), ignore_errors=True)
