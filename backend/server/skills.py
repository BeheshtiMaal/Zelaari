"""Skills, their switches, slash commands, the marketplace and the search provider."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from permissions.types import ApprovalRecord
from skills import marketplace, state
from skills.registry import Registry
from skills.search import SearchSettings
from skills.settings import load_search
from skills.types import (
    MarketplaceCatalog,
    SkillCommand,
    SkillDetail,
    SkillEnabledInput,
    SkillInstallInput,
    SkillRecord,
    SkillsResponse,
    SkillWriteInput,
)
from store.actions import ActionApprovals
from tools.jail import JailError, workspace_root


class MarketplaceUrl(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class InstallRequest(SkillInstallInput):
    pass


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def _registry(root: Path, app_data: Path | None) -> Registry:
    return Registry.build(root, app_data)


def response(root: Path, registry: Registry) -> SkillsResponse:
    usable = [record for record in registry.records if not record.problem]
    broken = [record for record in registry.records if record.problem]
    switches = state.load_state(root)
    cached = marketplace.cache(root)
    return SkillsResponse(
        workspace=str(root),
        skills=usable,
        problems=broken,
        commands=registry.commands(),
        catalog_url=switches.catalog_url,
        fetched_at=cached.fetched_at if cached else None,
    )


def skills_routes(actions: ActionApprovals, app_data: Path | None) -> APIRouter:
    router = APIRouter()

    @router.get("/skills")
    def list_skills(workspace: str) -> SkillsResponse:
        root = _root(workspace)
        return response(root, _registry(root, app_data))

    @router.get("/skills/commands")
    def list_commands(workspace: str) -> list[SkillCommand]:
        return _registry(_root(workspace), app_data).commands()

    @router.get("/skills/marketplace")
    def read_marketplace(workspace: str) -> MarketplaceCatalog:
        root = _root(workspace)
        switches = state.load_state(root)
        cached = marketplace.cache(root)
        if cached is not None:
            return cached.model_copy(update={"catalog_url": switches.catalog_url})
        return MarketplaceCatalog(catalog_url=switches.catalog_url)

    @router.put("/skills/marketplace")
    def write_marketplace(workspace: str, value: MarketplaceUrl) -> MarketplaceCatalog:
        root = _root(workspace)
        try:
            url = marketplace.validate_url(value.url)
            catalog = marketplace.fetch(url)
        except (OSError, ValueError) as error:
            raise HTTPException(400, str(error)) from None
        state.set_catalog(root, url)
        marketplace.store(root, catalog)
        return catalog

    @router.put("/skills/enabled")
    def set_enabled(workspace: str, value: SkillEnabledInput) -> SkillRecord:
        root = _root(workspace)
        registry = _registry(root, app_data)
        record = registry.find(value.name)
        if record is None:
            raise HTTPException(404, "Unknown skill")
        state.set_enabled(root, value.name, value.enabled)
        updated = _registry(root, app_data).find(value.name)
        return updated or record

    @router.get("/skills/search")
    def read_search(workspace: str) -> SearchSettings:
        return load_search(_root(workspace))

    @router.put("/skills/search", status_code=202)
    def write_search(workspace: str, value: SearchSettings) -> ApprovalRecord:
        try:
            return actions.propose_search(_root(workspace), value)
        except (OSError, ValueError):
            raise HTTPException(409, "Workspace configuration needs repair") from None

    @router.post("/skills/install", status_code=202)
    def install(workspace: str, value: InstallRequest) -> ApprovalRecord:
        root = _root(workspace)
        try:
            return actions.propose_skill_install(root, value.kind, value.source, app_data)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.post("/skills/create", status_code=202)
    def create(workspace: str, value: SkillWriteInput) -> ApprovalRecord:
        try:
            return actions.propose_skill_write(_root(workspace), value, create=True)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.get("/skills/{name}")
    def read_skill(workspace: str, name: str) -> SkillDetail:
        registry = _registry(_root(workspace), app_data)
        record = registry.find(name)
        if record is None:
            raise HTTPException(404, "Unknown skill")
        return registry.detail(record)

    @router.put("/skills/{name}", status_code=202)
    def edit_skill(workspace: str, name: str, value: SkillWriteInput) -> ApprovalRecord:
        if name != value.name:
            raise HTTPException(400, "The name in the body must match the path")
        try:
            return actions.propose_skill_write(_root(workspace), value, create=False)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.delete("/skills/{name}", status_code=202)
    def delete_skill(workspace: str, name: str) -> ApprovalRecord:
        try:
            return actions.propose_skill_delete(_root(workspace), name)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    return router
