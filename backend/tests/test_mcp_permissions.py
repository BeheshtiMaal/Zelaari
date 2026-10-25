"""MCP tools pass the same gate as everything else, and never ride on Auto silently."""

from pathlib import Path

from permissions.rules import RulesEngine, category_of


def test_a_namespaced_tool_is_the_mcp_category() -> None:
    assert category_of("files__read") == "mcp"
    assert category_of("github__create_issue") == "mcp"


def test_built_in_tools_keep_their_category() -> None:
    assert category_of("read_file") == "read"
    assert category_of("write_file") == "write"
    assert category_of("load_skill") == "read"


def test_auto_still_asks_for_mcp(tmp_path: Path) -> None:
    engine = RulesEngine.load(tmp_path, "auto")
    outcome = engine.decide("files__read")
    assert outcome.action == "ask"
    assert "mcp" in outcome.reason


def test_read_only_denies_mcp(tmp_path: Path) -> None:
    engine = RulesEngine.load(tmp_path, "read-only")
    outcome = engine.decide("files__read")
    assert outcome.action == "deny"
    assert "read-only" in outcome.reason


def test_ask_mode_asks_for_mcp(tmp_path: Path) -> None:
    assert RulesEngine.load(tmp_path, "ask").decide("files__write").action == "ask"


def test_the_always_ask_list_names_mcp(tmp_path: Path) -> None:
    assert "MCP tool calls" in RulesEngine.load(tmp_path, "auto").always_ask()


def test_loading_a_skill_body_is_read_only(tmp_path: Path) -> None:
    outcome = RulesEngine.load(tmp_path, "read-only").decide("load_skill")
    assert outcome.action == "allow"
