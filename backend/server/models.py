"""Provider metadata routes. Credentials are write-only and never persisted here."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from providers.base import ModelInput, Preset, ProviderRecord, Settings
from providers.probe import test_connection
from store.catalog import Catalog, Credential


def model_routes(catalog: Catalog) -> APIRouter:
    router = APIRouter()

    @router.get("/models")
    def models() -> list[ProviderRecord]:
        return catalog.records()

    @router.post("/models")
    def save(value: ModelInput) -> ProviderRecord:
        try:
            return catalog.save(value)
        except (ValueError, OSError):
            raise HTTPException(400, "Model could not be saved") from None

    @router.post("/internal/credentials")
    def credentials(value: Credential) -> dict[str, str]:
        try:
            catalog.credential(value)
        except (ValueError, OSError):
            raise HTTPException(400, "Credential unavailable") from None
        return {"status": "ok"}

    @router.get("/presets")
    def presets() -> list[Preset]:
        path = Path(__file__).parents[1] / "providers" / "presets.json"
        return [Preset.model_validate(item) for item in json.loads(path.read_text())]

    @router.post("/models/{identifier}/test")
    async def probe(identifier: str) -> ProviderRecord:
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
