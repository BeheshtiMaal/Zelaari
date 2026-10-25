"""A web query is asked in every mode, and the query a person edits is the one that runs."""

from pathlib import Path
from typing import cast

import pytest
from langchain_core.messages import ToolCall

from permissions.middleware import PermissionMiddleware, tool_target
from permissions.rules import RulesEngine
from permissions.types import Mode, Rule, RulesFile
from skills.websearch import WebSearchInput


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("ask", "ask"), ("auto", "ask"), ("read-only", "deny")],
)
def test_every_mode_asks(tmp_path: Path, mode: str, expected: str) -> None:
    outcome = RulesEngine(tmp_path, cast(Mode, mode)).decide("web_search", command="pytest 8")
    assert outcome.action == expected


def test_an_explicit_allow_rule_is_the_only_way_through(tmp_path: Path) -> None:
    rules = RulesFile(
        mode="auto", tools={"web_search": [Rule(glob="*", action="allow")]}
    )
    allowed = RulesEngine(tmp_path, "auto", rules).decide("web_search", command="q")
    assert allowed.action == "allow"
    # Read-only is a ceiling: a rule cannot lift it.
    denied = RulesEngine(tmp_path, "read-only", rules).decide("web_search", command="q")
    assert denied.action == "deny"


def test_the_approval_card_shows_the_query(tmp_path: Path) -> None:
    middleware = PermissionMiddleware(RulesEngine(tmp_path, "auto"), run_id="r")
    call = ToolCall(
        name="web_search", args={"query": "deepagents 0.7.28 release notes"}, id="call-1"
    )
    assert tool_target("web_search", call["args"]) == (
        None,
        "deepagents 0.7.28 release notes",
        None,
    )
    request = middleware.approval(call, middleware.decide(call))
    assert request.command == "deepagents 0.7.28 release notes"
    assert request.tool == "web_search"
    assert request.args["query"] == "deepagents 0.7.28 release notes"
    assert "web query" in request.reason


def test_an_edited_query_must_still_be_valid() -> None:
    assert WebSearchInput(query="a" * 400).query == "a" * 400
    with pytest.raises(ValueError):
        WebSearchInput(query="a" * 401)
    with pytest.raises(ValueError):
        WebSearchInput(query="first\nsecond")
    with pytest.raises(ValueError):
        WebSearchInput(query="   ")
