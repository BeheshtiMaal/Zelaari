"""Atomic question ledger; accepted decisions outlive the graph process."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from questions.types import QuestionAnswer, QuestionRecord, QuestionRequest
from tools.atomic import atomic_write

adapter = TypeAdapter(dict[str, QuestionRecord])


class QuestionLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records = adapter.validate_json(path.read_bytes()) if path.exists() else {}

    def save(self) -> None:
        atomic_write(self.path, adapter.dump_json(self.records).decode())

    def announce(self, request: QuestionRequest, interrupt_id: str) -> QuestionRecord:
        old = self.records.get(request.call_id)
        if old:
            if old.interrupt_id != interrupt_id or old.request.questions != request.questions:
                raise ValueError("Question call identity was reused")
            return old
        record = QuestionRecord(request=request, interrupt_id=interrupt_id)
        self.records[request.call_id] = record
        self.save()
        return record

    def answer(self, answer: QuestionAnswer) -> None:
        record = self.records.get(answer.call_id)
        if not record or record.status != "pending" or record.interrupt_id != answer.interrupt_id:
            raise ValueError("Question is not pending in this interrupt")
        answer.validate_request(record.request)
        record.answer = answer
        record.status = answer.status
        record.resolved_at = datetime.now(UTC)
        self.save()

    def cancel(self, *, persist: bool = True) -> None:
        changed = False
        for record in self.records.values():
            if record.status == "pending":
                record.status = "cancelled"
                record.resolved_at = datetime.now(UTC)
                changed = True
        if persist and changed:
            self.save()
