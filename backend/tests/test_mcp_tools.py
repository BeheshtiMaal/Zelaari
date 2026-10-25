"""MCP tools become ordinary LangChain tools with a validated argument model."""

import sys
from pathlib import Path

from connectors.client import McpError, ToolSpec
from connectors.config import McpServerConfig
from connectors.tools import Connectors, arguments_model, build, tool_for

WORKER = Path(__file__).with_name("mcp_worker.py")


def server(mode: str = "normal", name: str = "fixture") -> McpServerConfig:
    return McpServerConfig(name=name, command=[sys.executable, str(WORKER), mode])


def test_a_json_schema_becomes_a_pydantic_model() -> None:
    spec = ToolSpec(
        name="echo",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "limit": {"type": "integer"},
                "weird name": {"type": "string"},
            },
            "required": ["text"],
        },
    )
    model = arguments_model("echo", spec)
    assert set(model.model_fields) == {"text", "limit"}
    assert model.model_fields["text"].is_required() is True
    assert model.model_fields["limit"].is_required() is False
    assert model.model_validate({"text": "hi"}).model_dump() == {"text": "hi", "limit": None}


def test_an_empty_schema_accepts_no_arguments() -> None:
    model = arguments_model("ping", ToolSpec(name="ping"))
    assert model().model_dump() == {}


def test_a_tool_is_namespaced_and_calls_the_session() -> None:
    class Fake:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def list_tools(self) -> list[ToolSpec]:
            return []

        def call(self, name: str, arguments: dict[str, object]) -> str:
            self.calls.append((name, arguments))
            return "ok"

        def close(self) -> None:
            return None

    fake = Fake()
    tool = tool_for(fake, "files", ToolSpec(name="read", description="Read a file."))
    assert tool.name == "files__read"
    assert tool.description == "Read a file."
    assert tool.invoke({}) == "ok"
    assert fake.calls == [("read", {})]


def test_a_failed_call_is_returned_not_raised() -> None:
    class Broken:
        def list_tools(self) -> list[ToolSpec]:
            return []

        def call(self, name: str, arguments: dict[str, object]) -> str:
            raise McpError("gone")

        def close(self) -> None:
            return None

    tool = tool_for(Broken(), "files", ToolSpec(name="read"))
    assert tool.invoke({}) == "Error: gone"


def test_build_keeps_working_tools_when_one_server_fails(tmp_path: Path) -> None:
    found = build(
        tmp_path,
        [
            server(),
            McpServerConfig(name="gone", command=["definitely-not-installed-binary"]),
        ],
        timeout=10,
    )
    try:
        assert [tool.name for tool in found.tools] == ["fixture__echo", "fixture__count"]
        assert "gone" in found.errors
        assert found.tools[0].invoke({"text": "hi"}) == "echo: hi"
    finally:
        found.close()


def test_a_disabled_server_contributes_nothing(tmp_path: Path) -> None:
    off = McpServerConfig(
        name="gone", command=["definitely-not-installed-binary"], enabled=False
    )
    found = build(tmp_path, [off])
    assert found.tools == []
    assert found.errors == {}


def test_close_is_idempotent(tmp_path: Path) -> None:
    found = build(tmp_path, [server()], timeout=10)
    found.close()
    found.close()
    assert found.sessions == []
    assert isinstance(Connectors(), Connectors)
