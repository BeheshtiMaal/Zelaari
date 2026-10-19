"""Atomic approval ledger, independent of a live graph or renderer connection."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from permissions.types import ApprovalAnswer, ApprovalRecord, ApprovalRequest, UnknownApproval
from tools.atomic import atomic_write

records_adapter = TypeAdapter(dict[str, ApprovalRecord])


class ApprovalLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records = records_adapter.validate_json(path.read_bytes()) if path.exists() else {}

    def save(self) -> None:
        atomic_write(self.path, records_adapter.dump_json(self.records).decode())

    def announce(self, request: ApprovalRequest, interrupt_id: str) -> ApprovalRecord:
        existing = self.records.get(request.approval_id)
        if existing is not None:
            return existing
        record = ApprovalRecord(request=request, interrupt_id=interrupt_id)
        self.records[request.approval_id] = record
        self.save()
        return record

    def answer(self, answer: ApprovalAnswer) -> None:
        record = self.records.get(answer.approval_id)
        if record is None or record.status != "pending":
            raise UnknownApproval(answer.approval_id)
        record.answer = answer
        record.status = "approved" if answer.decision == "approve" else "rejected"
        record.resolved_at = datetime.now(UTC)
        self.save()

    def cancel(self) -> None:
        for record in self.records.values():
            if record.status == "pending":
                record.status = "cancelled"
                record.resolved_at = datetime.now(UTC)
        self.save()
