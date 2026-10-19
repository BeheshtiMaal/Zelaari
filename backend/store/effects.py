"""Write-ahead effect records. An incomplete intent is never dispatched twice."""

from pathlib import Path

from pydantic import TypeAdapter

from permissions.types import CommandJournalEntry
from tools.atomic import atomic_write

adapter = TypeAdapter(dict[str, CommandJournalEntry])


class EffectJournal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, CommandJournalEntry]:
        return adapter.validate_json(self.path.read_bytes()) if self.path.exists() else {}

    def begin(self, call_id: str, digest: str) -> CommandJournalEntry | None:
        records = self.read()
        previous = records.get(call_id)
        if previous:
            if previous.args_digest != digest:
                raise ValueError("Effect identity already belongs to different arguments")
            return previous
        records[call_id] = CommandJournalEntry(call_id=call_id, args_digest=digest)
        atomic_write(self.path, adapter.dump_json(records).decode())
        return None

    def complete(self, call_id: str, result: str) -> None:
        records = self.read()
        records[call_id].status = "completed"
        records[call_id].result = result
        atomic_write(self.path, adapter.dump_json(records).decode())
