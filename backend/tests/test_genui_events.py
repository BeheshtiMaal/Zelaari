"""One durable `ui.render` per attempt, success or failure, so a replay redraws the same UI."""

import asyncio
import json
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from agent.events import UiRender
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from planning.types import ActivityScope
from store.eventlog import EventBus
from store.secrets import Redactor

PROGRAM = 'root = Stack([c])\nc = Callout("three files")'


def project(
    tmp_path: Path,
    content: str,
    *,
    program: str = PROGRAM,
    redactor: Redactor | None = None,
) -> tuple[list[UiRender], Path]:
    directory = tmp_path / "run"
    directory.mkdir()
    bus = EventBus(directory / "events.jsonl", "run", redactor or Redactor())
    projection = ActivityProjection(bus, TokenMeter(0), 128_000, False)
    projection.scopes[()] = ActivityScope(scope_id="scope")

    async def scenario() -> None:
        await projection.update(
            (),
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            id="ai-1",
                            tool_calls=[
                                {"name": "render_ui", "id": "call-1", "args": {"ui": program}}
                            ],
                        )
                    ]
                }
            },
        )
        await projection.update(
            (),
            {
                "tools": {
                    "messages": [
                        ToolMessage(content=content, tool_call_id="call-1", name="render_ui")
                    ]
                }
            },
        )

    asyncio.run(scenario())
    return [event for event in bus.history if isinstance(event, UiRender)], directory


def test_a_successful_render_is_persisted_with_its_program(tmp_path: Path) -> None:
    events, directory = project(
        tmp_path, json.dumps({"ok": True, "components": ["Stack", "Callout"], "statements": 2})
    )
    assert len(events) == 1
    event = events[0]
    assert (event.ok, event.call_id, event.statements) == (True, "call-1", 2)
    assert event.components == ["Stack", "Callout"]
    assert event.text == PROGRAM
    assert event.error is None
    persisted = [
        json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()
    ]
    assert [item["type"] for item in persisted].count("ui.render") == 1


def test_a_rejected_program_keeps_the_reason(tmp_path: Path) -> None:
    events, _ = project(
        tmp_path, json.dumps({"ok": False, "error": 'line 2: unknown component "Chart"'})
    )
    assert len(events) == 1
    assert events[0].ok is False
    assert events[0].error == 'line 2: unknown component "Chart"'
    assert events[0].text == PROGRAM


def test_a_tool_contract_error_is_still_a_visible_failure(tmp_path: Path) -> None:
    events, _ = project(tmp_path, "ui: String should have at most 20000 characters")
    assert len(events) == 1
    assert events[0].ok is False
    assert events[0].error is not None and "20000" in events[0].error


def test_the_program_is_redacted_before_it_is_persisted(tmp_path: Path) -> None:
    secret = "sk-live-424242"
    events, directory = project(
        tmp_path,
        json.dumps({"ok": True, "components": ["Stack"], "statements": 1}),
        program=f'root = Stack([c])\nc = Callout("{secret}")',
        redactor=Redactor([secret]),
    )
    assert secret not in events[0].text
    assert secret not in (directory / "events.jsonl").read_text(encoding="utf-8")
