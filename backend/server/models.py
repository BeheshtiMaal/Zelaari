"""Provider metadata routes. Credentials are write-only and never persisted here."""

import asyncio
import importlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import SecretStr

from providers.base import ModelInput, Preset, ProviderRecord, Settings
from store.catalog import Catalog, Credential


class DraftModel(ModelInput):
    key: SecretStr


def model_routes(catalog: Catalog) -> APIRouter:
    router = APIRouter()

    @router.post("/internal/probe")
    async def draft_probe(value: DraftModel) -> ProviderRecord:
        await asyncio.to_thread(importlib.import_module, "providers.probe")
        from providers.probe import test_connection

        temporary = Catalog(redactor=catalog.redactor)
        temporary.credential(Credential(id=value.id, key=value.key))
        temporary.save(ModelInput.model_validate(value.model_dump(exclude={"key"})))
        return await test_connection(temporary, value.id)

    @router.get("/models")
    def models() -> list[ProviderRecord]:
        return catalog.records()

    @router.post("/models")
    async def save(value: ModelInput) -> ProviderRecord:
        try:
            from providers.context import detect_context, model_metadata

            record = catalog.save(value)
            record.context = detect_context(
                record.model, await model_metadata(record, catalog.keys[value.id])
            )
            catalog.persist()
            return record
        except (ValueError, OSError):
            raise HTTPException(400, "Model could not be saved") from None

    @router.post("/internal/credentials")
    def credentials(value: Credential) -> dict[str, str]:
        try:
            catalog.credential(value)
        except (ValueError, OSError):
            raise HTTPException(400, "Credential unavailable") from None
        return {"status": "ok"}

    @router.delete("/internal/credentials")
    def clear_credentials() -> dict[str, int]:
        """The renderer's "delete all keys". Counts only; no key is ever echoed back."""
        return {"keys": catalog.clear_credentials()}

    @router.get("/presets")
    def presets() -> list[Preset]:
        path = Path(__file__).parents[1] / "providers" / "presets.json"
        return [Preset.model_validate(item) for item in json.loads(path.read_text())]

    @router.post("/models/{identifier}/test")
    async def probe(identifier: str) -> ProviderRecord:
        await asyncio.to_thread(importlib.import_module, "providers.probe")
        from providers.probe import test_connection

        try:
            return await test_connection(catalog, identifier)
        except (ValueError, OSError):
            raise HTTPException(400, "Model test unavailable") from None

    @router.get("/settings")
    def settings() -> Settings:
        return catalog.data.settings

    @router.put("/settings")
    def update_settings(value: Settings) -> Settings:
        try:
            return catalog.settings(value)
        except (ValueError, OSError):
            raise HTTPException(400, "Choose a tested model") from None

    return router
