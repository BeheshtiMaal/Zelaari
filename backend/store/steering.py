"""Run-owned durable steering queue; graph checkpoints acknowledge delivery."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from planning.types import SteeringRecord, SteeringSubmission
from store.eventlog import EventBus
from tools.atomic import atomic_write

adapter = TypeAdapter(list[SteeringRecord])


class SteeringQueue:
    def __init__(self, path: Path, run_id: str) -> None:
        self.path, self.run_id = path, run_id
        self.records = adapter.validate_json(path.read_bytes()) if path.exists() else []
        if any(record.run_id != run_id for record in self.records):
            raise ValueError("Steering queue identity mismatch")

    def save(self) -> None:
        atomic_write(self.path, adapter.dump_json(self.records).decode())

    def enqueue(self, value: SteeringSubmission, *, terminal: bool) -> SteeringRecord:
        existing = next((r for r in self.records if r.submission_id == value.submission_id), None)
        if existing:
            if existing.text != value.text:
                raise ValueError("Submission identity was reused")
            return existing
        if terminal:
            raise ValueError("Run has finished")
        record = SteeringRecord(
            **value.model_dump(),
            run_id=self.run_id,
            ordinal=len(self.records) + 1,
            queued_at=datetime.now(UTC),
        )
        self.records.append(record)
        self.save()
        return record

    def pending(self) -> list[SteeringRecord]:
        return [record for record in self.records if record.status == "queued"]

    def reconcile(self, state: dict[str, Any]) -> None:
        seen = set(state.get("steering_seen", []))
        changed = False
        for record in self.records:
            if record.submission_id in seen and record.status == "queued":
                record.status = "delivered"
                record.delivered_at = datetime.now(UTC)
                changed = True
        if changed:
            self.save()

    def cancel(self) -> None:
        for record in self.pending():
            record.status = "cancelled"
        self.save()

    async def publish(self, bus: EventBus) -> None:
        for record in self.records:
            previous = next(
                (
                    event.message
                    for event in reversed(bus.history)
                    if event.type == "steering.updated"
                    and event.message.submission_id == record.submission_id
                ),
                None,
            )
            if previous != record:
                await bus.emit("steering.updated", message=record)
