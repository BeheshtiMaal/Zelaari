import inspect
import json
import socket
from pathlib import Path
from typing import Any

import pytest
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from demo import DemoModel, call


@tool
def echo(value: str) -> str:
    """Return the supplied value for the spike."""
    return "echo:" + value


def test_api_activity_and_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Network is forbidden during demo invocation")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    required = {
        "backend",
        "skills",
        "memory",
        "subagents",
        "middleware",
        "checkpointer",
        "interrupt_on",
        "system_prompt",
    }
    assert required <= set(inspect.signature(create_deep_agent).parameters)
    (tmp_path / "memory.md").write_text("SPIKE_MEMORY_MARKER", encoding="utf8")
    skills = tmp_path / "skills" / "sample"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: sample\ndescription: SPIKE_SKILL_MARKER\n---\nUse a fixture.\n", encoding="utf8"
    )
    model = DemoModel(
        script=[
            call(
                "write_todos",
                {"todos": [{"content": "Inspect fixture", "status": "in_progress"}]},
                "todos",
            ),
            call(
                "task", {"description": "Inspect fixture", "subagent_type": "reviewer"}, "delegate"
            ),
            call("echo", {"value": "fixture"}, "echo"),
            AIMessage(content="Demo finished"),
        ]
    )
    reviewer = DemoModel(script=[AIMessage(content="Review complete")])
    agent = create_deep_agent(
        model=model,
        tools=[echo],
        system_prompt="SPIKE_AUTHORED_PROMPT",
        backend=FilesystemBackend(root_dir=tmp_path, virtual_mode=True),
        memory=["/memory.md"],
        skills=["/skills/"],
        middleware=[TodoListMiddleware()],
        checkpointer=InMemorySaver(),
        subagents=[
            {
                "name": "reviewer",
                "description": "Inspect fixtures",
                "model": reviewer,
                "system_prompt": "Inspect only",
                "tools": [],
            }
        ],
    )
    events = list(
        agent.stream(
            {"messages": [{"role": "user", "content": "Run demo"}]},
            config={"configurable": {"thread_id": "demo"}},
            stream_mode=["messages", "updates"],
            subgraphs=True,
        )
    )
    assert {"write_todos", "task", "echo"} <= set(model.bound_names)
    snapshot = repr(events)
    assert "write_todos" in snapshot and "task" in snapshot and "echo:fixture" in snapshot
    assert "Demo " in snapshot and "finished " in snapshot
    assert reviewer.requests
    system = "\n".join(str(m.content) for m in model.requests[0] if isinstance(m, SystemMessage))
    assert "SPIKE_AUTHORED_PROMPT" in system
    assert "SPIKE_MEMORY_MARKER" in system and "SPIKE_SKILL_MARKER" in system
    assert "You are a deep agent, an AI assistant" not in system
    artifacts = Path(__file__).resolve().parents[2] / "artifacts"
    artifacts.mkdir(exist_ok=True)
    summary = [
        {
            "namespace": list(namespace),
            "mode": mode,
            "keys": list(payload) if isinstance(payload, dict) else [],
            "node": payload[1].get("langgraph_node")
            if mode == "messages" and isinstance(payload, tuple) and isinstance(payload[1], dict)
            else None,
        }
        for namespace, mode, payload in events
    ]
    (artifacts / "agent-stream.json").write_text(json.dumps(summary, indent=2), encoding="utf8")


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_interrupt_resume(decision: str) -> None:
    model = DemoModel(
        script=[call("echo", {"value": "approved"}, "one"), AIMessage(content="Done")]
    )
    agent = create_deep_agent(
        model=model, tools=[echo], checkpointer=InMemorySaver(), interrupt_on={"echo": True}
    )
    config: RunnableConfig = {"configurable": {"thread_id": decision}}
    result = agent.invoke({"messages": [{"role": "user", "content": "Try echo"}]}, config)
    interrupt = result["__interrupt__"][0]
    assert interrupt.value["action_requests"][0]["name"] == "echo"
    artifacts = Path(__file__).resolve().parents[2] / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / f"interrupt-{decision}.json").write_text(
        json.dumps(interrupt.value, indent=2), encoding="utf8"
    )
    assert not any(isinstance(m, ToolMessage) for m in result["messages"])
    payload: dict[str, Any] = {"type": decision}
    if decision == "reject":
        payload["message"] = "Human declined"
    result = agent.invoke(Command(resume={"decisions": [payload]}), config)
    tools = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tools) == 1
    assert ("echo:approved" in str(tools[0].content)) == (decision == "approve")
    assert not result.get("__interrupt__")
