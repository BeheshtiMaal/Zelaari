"""Subprocess fixture for actual engine termination; never loaded by the product."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

import agent.bridge
from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision
from providers.demo import DemoModel
from store.catalog import Catalog
from store.effects import EffectJournal


class RecoveryModel(DemoModel):
    scenario: str

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        results = [message for message in messages if isinstance(message, ToolMessage)]
        names = {message.name for message in results}
        if "submit_plan" not in names:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "submit_plan",
                        "id": "recovery-plan",
                        "args": {
                            "steps": [
                                {
                                    "id": "effect",
                                    "title": "Exercise recovery",
                                    "expected_files": ["a.txt", "b.txt"]
                                    if self.scenario == "pending"
                                    else [],
                                }
                            ]
                        },
                    }
                ],
            )
        if "write_todos" not in names:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_todos",
                        "id": "recovery-progress",
                        "args": {
                            "todos": [
                                {"content": "[effect] Exercise recovery", "status": "in_progress"}
                            ]
                        },
                    }
                ],
            )
        if any(message.name not in {"submit_plan", "write_todos"} for message in results):
            return AIMessage(content='root = Callout("done");')
        if self.scenario == "pending":
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "write_file", "args": {"file_path": name, "content": name}, "id": key}
                    for name, key in (("a.txt", "one"), ("b.txt", "two"))
                ],
            )
        command = "Set-Content shell.pid $PID; Add-Content -Path launches.txt -Value launch"
        if self.scenario == "executing":
            command += "; Start-Sleep -Seconds 60"
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "run_command",
                    "args": {"command": command},
                    "id": "command-one",
                }
            ],
        )


async def main() -> None:
    root, scenario, stage = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    setattr(agent.bridge, "DemoModel", lambda **kwargs: RecoveryModel(scenario=scenario, delay=0))
    manager = RunManager(catalog=Catalog(root.parent / "catalog.json"))
    if stage == "resume":
        await manager.recover()
        run_id = manager.catalog.data.workspaces.tasks[0].id
        while (
            run_id not in manager.runs or not manager.runs[run_id].barrier and scenario == "pending"
        ):
            await asyncio.sleep(0.01)
        if scenario == "pending":
            await manager.resolve(run_id, "one", ApprovalDecision(decision="approve"))
        while not manager.runs[run_id].bus.finished:
            await asyncio.sleep(0.01)
        print(json.dumps({"finished": True}), flush=True)
        await manager.close()
        return
    if scenario == "after-result":

        def die(self: Any, call_id: str, result: str) -> None:
            os._exit(71)

        EffectJournal.complete = die  # type: ignore[method-assign]
    run_id = await manager.start(RunRequest(task="recovery fixture", workspace=str(root)))
    while len(manager.approvals("pending")) < (2 if scenario == "pending" else 1):
        await asyncio.sleep(0.01)
    if scenario == "pending":
        await manager.resolve(run_id, "two", ApprovalDecision(decision="reject", reason="keep b"))
    else:
        await manager.resolve(run_id, "command-one", ApprovalDecision(decision="approve"))
        while not (root / "launches.txt").exists():
            await asyncio.sleep(0.01)
    print(json.dumps({"run_id": run_id, "ready": True}), flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
