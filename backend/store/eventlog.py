"""One ordered durable event stream per run, with race-free live subscriptions."""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from agent.events import Event, event_adapter
from store.secrets import Redactor


class EventBus:
    def __init__(self, path: Path, run_id: str, redactor: Redactor) -> None:
        self.path = path
        self.run_id = run_id
        self.redactor = redactor
        path.parent.mkdir(parents=True, exist_ok=True)
        self.history: list[Event] = []
        if path.exists():
            payload = path.read_bytes()
            lines = payload.splitlines(keepends=True)
            valid = 0
            for index, line in enumerate(lines):
                try:
                    event = event_adapter.validate_json(line)
                except ValueError:
                    if index == len(lines) - 1 and not line.endswith(b"\n"):
                        # A killed append can leave only the final record incomplete.
                        with path.open("r+b") as stream:
                            stream.truncate(valid)
                        break
                    raise
                if event.run_id != run_id or event.seq != len(self.history) + 1:
                    raise ValueError("Event log identity or sequence mismatch")
                self.history.append(event)
                valid += len(line)
        self.changed = asyncio.Condition()
        self.finished = bool(self.history and self.history[-1].type == "run.finished")

    async def emit(self, event_type: str, /, **payload: Any) -> None:
        # Positional-only: payloads may legitimately contain a `kind` or `type` field.
        await self.emit_many([(event_type, payload)])

    async def emit_many(self, values: list[tuple[str, dict[str, Any]]]) -> None:
        """Commit a terminal transition atomically with one durable flush."""
        async with self.changed:
            if self.finished:
                return
            events: list[Event] = []
            for kind, payload in values:
                if events and events[-1].type == "run.finished":
                    raise ValueError("Terminal event must be last")
                event = event_adapter.validate_python(
                    {
                        **payload,
                        "type": kind,
                        "run_id": self.run_id,
                        "seq": len(self.history) + len(events) + 1,
                    }
                )
                events.append(
                    event_adapter.validate_python(
                        self.redactor.value(event.model_dump(mode="json"))
                    )
                )
            if not events:
                return
            with self.path.open("a", encoding="utf-8", newline="\n") as log:
                log.write("".join(event.model_dump_json() + "\n" for event in events))
                log.flush()
                os.fsync(log.fileno())
            self.history.extend(events)
            self.finished = events[-1].type == "run.finished"
            self.changed.notify_all()

    async def events(self, after: int) -> AsyncIterator[Event]:
        cursor = after
        while True:
            async with self.changed:
                await self.changed.wait_for(lambda: len(self.history) > cursor or self.finished)
                batch = self.history[cursor:]
                done = self.finished
            for event in batch:
                cursor = event.seq
                yield event
            if done:
                return
