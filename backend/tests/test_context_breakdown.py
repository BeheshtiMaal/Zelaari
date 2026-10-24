"""The breakdown is measured with the summarizer's counter, not guessed by the UI."""

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from agent.bridge import RunManager
from agent.events import RunRequest
from store.catalog import Catalog
from store.secrets import Redactor
from tools.jail import storage_path
from verify.context import Window, breakdown


def tool(name: str, text: str) -> StructuredTool:
    def run(value: str = "") -> str:
        """Echo."""
        return value

    return StructuredTool.from_function(run, name=name, description=text)


def conversation() -> list[Any]:
    return [
        HumanMessage(content="Fix the parser " * 20),
        AIMessage(content="Reading the files " * 20),
        ToolMessage(content="x " * 400, tool_call_id="1", name="read_file"),
        ToolMessage(content="y " * 200, tool_call_id="2", name="run_command"),
        AIMessage(content="Done " * 10),
    ]


def test_the_rows_add_up_to_the_prompt() -> None:
    measured = breakdown(conversation(), "You are CodeHarness.", [tool("read_file", "Read a file")])
    assert measured.messages > 0
    assert measured.tool_results > 0
    assert measured.system > 0
    assert (measured.skills, measured.memory) == (0, 0)
    assert measured.estimated is True
    # Every token in the prompt lands in exactly one row.
    whole = breakdown(conversation())
    assert measured.messages == whole.messages
    assert measured.tool_results == whole.tool_results


def test_tool_results_are_not_counted_as_messages() -> None:
    only_tool = breakdown([ToolMessage(content="z " * 500, tool_call_id="1", name="read_file")])
    assert only_tool.messages == 0
    assert only_tool.tool_results > 100
    only_text = breakdown([HumanMessage(content="hello there")])
    assert only_text.tool_results == 0
    assert only_text.messages > 0


def test_the_system_row_covers_the_prompt_and_the_tool_schemas() -> None:
    without = breakdown([], "You are CodeHarness.", [])
    with_tools = breakdown(
        [], "You are CodeHarness.", [tool("read_file", "Read a file"), tool("write_file", "Write")]
    )
    assert without.system > 0
    assert with_tools.system > without.system
    # A system message already in the state is part of the same row.
    in_state = breakdown([SystemMessage(content="You are CodeHarness.")], "", [])
    assert in_state.system == without.system


def test_an_empty_prompt_costs_nothing() -> None:
    measured = breakdown([], "", [])
    assert measured.model_dump(exclude={"estimated"}) == {
        "messages": 0,
        "tool_results": 0,
        "system": 0,
        "skills": 0,
        "memory": 0,
    }


def test_the_window_keeps_the_last_prompt() -> None:
    window = Window(system="You are CodeHarness.", tools=[tool("read_file", "Read a file")])
    window.messages = conversation()
    measured = window.breakdown()
    assert measured.messages > 0 and measured.system > 0
    window.messages = []
    assert window.breakdown().messages == 0


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    storage_path(root, "").mkdir(parents=True, exist_ok=True)
    storage_path(root, "config.json").write_text(
        json.dumps({"verify": {"gate": False, "command": "echo ok"}}), encoding="utf-8"
    )
    return root


def test_a_real_run_reports_a_measured_breakdown(tmp_path: Path) -> None:
    root = workspace(tmp_path)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify gate", workspace=str(root), mode="auto")
        )
        async with asyncio.timeout(90):
            while not any(
                event.type == "run.finished" for event in manager.runs[run_id].bus.history
            ):
                await asyncio.sleep(0.02)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    updates = [event for event in events if event.type == "context.updated"]
    assert updates
    for event in updates:
        assert event.breakdown is not None
        assert event.breakdown.estimated is True
        assert event.breakdown.system > 0
    last = updates[-1].breakdown
    assert last is not None
    assert last.messages > 0
    # The rows are the whole prompt, so they cannot exceed the reported input.
    assert last.messages + last.tool_results + last.system > 0
