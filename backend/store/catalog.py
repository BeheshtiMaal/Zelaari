"""Atomic app-data metadata and memory-only credentials."""

from hashlib import sha256
from pathlib import Path
from threading import RLock

from pydantic import Field, SecretStr

from providers.base import (
    ModelInput,
    Probe,
    ProviderRecord,
    Record,
    Settings,
    WorkspaceState,
    infer_kind,
)
from store.secrets import Redactor


class CatalogData(Record):
    key_digests: dict[str, str] = Field(default_factory=dict)
    models: dict[str, ProviderRecord] = Field(default_factory=dict)
    settings: Settings = Field(default_factory=Settings)
    workspaces: WorkspaceState = Field(default_factory=WorkspaceState)


class Credential(Record):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    key: SecretStr


class Catalog:
    def __init__(self, path: Path | None = None, redactor: Redactor | None = None) -> None:
        self.lock = RLock()
        self.path = path
        self.redactor = redactor or Redactor()
        self.keys: dict[str, SecretStr] = {}
        self.data = CatalogData()
        if path and path.exists():
            self.data = CatalogData.model_validate_json(path.read_text(encoding="utf-8"))
            for model in self.data.models.values():
                if model.probe.status in {"testing", "retrying"}:
                    model.probe = Probe()
                    model.supports_tools = False
            for task in self.data.workspaces.tasks:
                if task.status == "running":
                    task.status = "interrupted"

    def persist(self) -> None:
        with self.lock:
            self._persist()

    def _persist(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(self.data.model_dump_json(), encoding="utf-8")
            temporary.replace(self.path)

    def credential(self, value: Credential) -> None:
        key = value.key.get_secret_value()
        if not key or len(key) > 16384 or value.id == "demo":
            raise ValueError("Invalid credential")
        old_digest = self.data.key_digests.get(value.id)
        digest = sha256(key.encode()).hexdigest()
        self.redactor.add(key)
        self.keys[value.id] = value.key
        self.data.key_digests[value.id] = digest
        model = self.data.models.get(value.id)
        if model:
            model.key_suffix = key[-4:] if len(key) > 4 else ""
            # A restart restore retains test status; a changed key invalidates it.
            if old_digest != digest:
                model.probe = Probe()
                model.supports_tools = False
            self.persist()

    def records(self) -> list[ProviderRecord]:
        demo = ProviderRecord(
            name="Demo", model="demo", kind="demo", supports_tools=True, probe=Probe(status="ok")
        )
        values = [demo]
        for record in self.data.models.values():
            public = record.model_copy(deep=True)
            if record.id not in self.keys:
                public.supports_tools = False
                public.probe = Probe(status="error", code="vault")
            values.append(public)
        return values

    def save(self, value: ModelInput) -> ProviderRecord:
        if value.id == "demo" or value.id not in self.keys:
            raise ValueError("Model requires a vault credential")
        # Provider display fields must never turn a submitted key into metadata.
        if self.redactor.text(value.model_dump_json()) != value.model_dump_json():
            raise ValueError("Secret in metadata")
        old = self.data.models.get(value.id)
        same = old and old.base_url == value.base_url and old.model == value.model
        record = ProviderRecord(
            **value.model_dump(),
            kind=infer_kind(value.base_url),
            api_key_ref=value.id,
            key_suffix=self.keys[value.id].get_secret_value()[-4:]
            if len(self.keys[value.id].get_secret_value()) > 4
            else "",
        )
        if same and old:
            record.probe, record.supports_tools, record.context = (
                old.probe,
                old.supports_tools,
                old.context,
            )
        self.data.models[value.id] = record
        self.persist()
        return record

    def require(self, identifier: str) -> ProviderRecord:
        record = next((item for item in self.records() if item.id == identifier), None)
        if record is None or not record.supports_tools or record.probe.status != "ok":
            raise ValueError("Test a usable model first")
        return record.model_copy(deep=True)

    def settings(self, value: Settings) -> Settings:
        if value.default_model:
            self.require(value.default_model)
        self.data.settings = value
        self.persist()
        return value
