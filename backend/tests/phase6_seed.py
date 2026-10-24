"""Seed a real low-threshold summary run for the Electron replay walkthrough."""

import asyncio
import sys
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

import agent.bridge as bridge
from agent.events import RunRequest
from agent.factory import build_agent
from agent.summarization import RedactingSummarization, summary_backend
from providers.demo import DemoModel
from store.catalog import Catalog
from store.secrets import Redactor


class SummaryFixture(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if not any(isinstance(message, SystemMessage) for message in messages):
            return AIMessage(
                content="INTERNAL SUMMARY TEXT",
                additional_kwargs={
                    "reasoning_content": "INTERNAL SUMMARY REASONING",
                },
            )
        return AIMessage(content='root = Callout("Actual summarized history replayed.");')


class History(AgentMiddleware[Any, Any, Any]):
    async def abefore_agent(self, state: Any, runtime: Any) -> dict[str, Any]:
        messages: list[BaseMessage] = []
        for number in range(5):
            messages.extend(
                [
                    HumanMessage(content=f"Earlier local analysis {number}"),
                    AIMessage(content="Earlier observed response"),
                ]
            )
        return {"messages": messages}


async def main() -> None:
    profile, workspace = Path(sys.argv[1]), Path(sys.argv[2])
    original = build_agent

    def factory(*args: Any, **kwargs: Any) -> Any:
        model = SummaryFixture(delay=0)
        redactor = Redactor()
        args = (args[0], model, args[2], redactor)
        kwargs["extra_middleware"] = [
            *kwargs.get("extra_middleware", []),
            History(),
            RedactingSummarization(
                model,
                summary_backend(workspace, redactor),
                redactor,
                trigger=("messages", 4),
                keep=("messages", 2),
            ),
        ]
        return original(*args, **kwargs)

    setattr(bridge, "build_agent", factory)
    manager = bridge.RunManager(catalog=Catalog(profile / "catalog.json"), demo_delay=0)
    run_id = await manager.start(RunRequest(task="Actual summary replay", workspace=str(workspace)))
    await manager.runs[run_id].task
    assert any(event.type == "context.summarized" for event in manager.runs[run_id].bus.history)
    assert not any(
        "INTERNAL SUMMARY" in event.text
        for event in manager.runs[run_id].bus.history
        if event.type in {"message.delta", "reasoning.delta"}
    )
    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
