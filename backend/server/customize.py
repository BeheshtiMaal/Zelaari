"""The Customize hub: memory, workspace agents, and the counts its tabs show."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents import loader as agents
from agents import memory
from connectors.config import load as load_mcp
from permissions.types import ApprovalRecord
from skills.registry import Registry
from skills.types import (
    AgentDocument,
    AgentRecord,
    AgentWriteInput,
    CustomizeSettings,
    MemoryDocument,
)
from store.actions import ActionApprovals
from tools.jail import JailError, workspace_root


class MemoryWrite(BaseModel):
    content: str = Field(default="", max_length=32_768)


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def customize_routes(actions: ActionApprovals, app_data: Path | None) -> APIRouter:
    router = APIRouter()

    @router.get("/customize")
    def overview(workspace: str) -> CustomizeSettings:
        root = _root(workspace)
        registry = Registry.build(root, app_data)
        usable = [record for record in registry.records if not record.problem]
        document = memory.load(root)
        return CustomizeSettings(
            workspace=str(root),
            skills=len(usable),
            enabled_skills=len([record for record in usable if record.enabled]),
            agents=len(agents.discover(root)),
            servers=len(load_mcp(root).servers),
            memory_bytes=document.bytes,
        )

    @router.get("/memory")
    def read_memory(workspace: str) -> MemoryDocument:
        return memory.load(_root(workspace))

    @router.put("/memory", status_code=202)
    def write_memory(workspace: str, value: MemoryWrite) -> ApprovalRecord:
        try:
            return actions.propose_memory(_root(workspace), value.content)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.get("/agents")
    def list_agents(workspace: str) -> list[AgentRecord]:
        return agents.discover(_root(workspace))

    @router.get("/agents/{name}")
    def read_agent(workspace: str, name: str) -> AgentDocument:
        document = agents.read(_root(workspace), name)
        if document is None:
            raise HTTPException(404, "Unknown agent")
        return document

    @router.post("/agents", status_code=202)
    def create_agent(workspace: str, value: AgentWriteInput) -> ApprovalRecord:
        try:
            return actions.propose_agent_write(_root(workspace), value, create=True)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.put("/agents/{name}", status_code=202)
    def edit_agent(workspace: str, name: str, value: AgentWriteInput) -> ApprovalRecord:
        if name != value.name:
            raise HTTPException(400, "The name in the body must match the path")
        try:
            return actions.propose_agent_write(_root(workspace), value, create=False)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    @router.delete("/agents/{name}", status_code=202)
    def delete_agent(workspace: str, name: str) -> ApprovalRecord:
        try:
            return actions.propose_agent_delete(_root(workspace), name)
        except (OSError, ValueError) as error:
            raise HTTPException(409, str(error)) from None

    return router
