"""Persist completed read-only results before announcing graph tool completion."""

from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from planning.types import ActivityScope
from store.secrets import Redactor
from tools.atomic import atomic_write


class DelegateResult(BaseModel):
    scope: ActivityScope
    text: str
    arguments_digest: str


adapter = TypeAdapter(dict[str, DelegateResult])


class DelegateResults:
    def __init__(self, path: Path, redactor: Redactor) -> None:
        self.path, self.redactor = path, redactor
        self.records = adapter.validate_json(path.read_bytes()) if path.exists() else {}

    def complete(
        self, invocation: str, scope: ActivityScope, text: str, arguments_digest: str
    ) -> None:
        self.records[invocation] = DelegateResult(
            scope=ActivityScope.model_validate(self.redactor.value(scope.model_dump(mode="json"))),
            text=self.redactor.text(text),
            arguments_digest=arguments_digest,
        )
        atomic_write(self.path, adapter.dump_json(self.records).decode())
