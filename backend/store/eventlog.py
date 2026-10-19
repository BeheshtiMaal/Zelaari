"""One ordered durable event stream per run, with race-free live subscriptions."""

import asyncio
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
        self.changed = asyncio.Condition()
        self.finished = False

    async def emit(self, kind: str, **payload: Any) -> None:
        async with self.changed:
            if self.finished:
                return
            event = event_adapter.validate_python(
                {
                    **payload,
                    "type": kind,
                    "run_id": self.run_id,
                    "seq": len(self.history) + 1,
                }
            )
            event = event_adapter.validate_python(
                self.redactor.value(event.model_dump(mode="json"))
            )
            with self.path.open("a", encoding="utf-8", newline="\n") as log:
                log.write(event.model_dump_json() + "\n")
                log.flush()
            self.history.append(event)
            self.finished = kind == "run.finished"
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
