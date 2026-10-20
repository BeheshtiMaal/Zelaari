"""Exercise the installed summarizer's separate model call under the real factory."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.factory import build_agent
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from agent.summarization import RedactingSummarization
from providers.demo import DemoModel
from store.eventlog import EventBus
from store.secrets import Redactor
from tools.fs import WorkspaceBackend


class SecretSummary(DemoModel):
    secret: str = "summary-output-secret-canary"

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        return AIMessage(content="Actual summary " + self.secret)


def test_summary_and_normal_response_redacted_before_checkpoint_or_offload(tmp_path: Path) -> None:
    model = SecretSummary(delay=0)
    redactor = Redactor([model.secret])
    path = tmp_path / "summary.sqlite"

    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            summary = RedactingSummarization(
                model,
                WorkspaceBackend(tmp_path, redactor),
                redactor,
                trigger=("messages", 4),
                keep=("messages", 2),
            )
            graph = build_agent(tmp_path, model, saver, redactor, extra_middleware=[summary])
            messages = []
            for index in range(4):
                messages.extend(
                    [HumanMessage(content=f"Question {index}"), AIMessage(content="Earlier answer")]
                )
            bus = EventBus(tmp_path / "events.jsonl", "summary", redactor)
            projection = ActivityProjection(bus, TokenMeter(1), 32000)
            async for namespace, update in cast(
                AsyncIterator[tuple[tuple[str, ...], dict[str, Any]]],
                graph.astream(
                    {"messages": messages},
                    {"configurable": {"thread_id": "summary"}},
                    stream_mode="updates",
                    subgraphs=True,
                    durability="sync",
                ),
            ):
                await projection.update(namespace, update)
            snapshot = await graph.aget_state({"configurable": {"thread_id": "summary"}})
            transition = snapshot.values["_summarization_event"]
            assert transition["cutoff_index"] > 0
            assert "[REDACTED]" in transition["summary_message"].content
            assert model.secret not in transition["summary_message"].content
            assert model.secret not in str(snapshot.values["messages"])
            notices = [event for event in bus.history if event.type == "context.summarized"]
            assert len(notices) == 1
            assert notices[0].affected_messages == transition["cutoff_index"]
        for artifact in tmp_path.rglob("*"):
            if artifact.is_file():
                assert model.secret.encode() not in artifact.read_bytes()

    asyncio.run(scenario())
