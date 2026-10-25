"""`render_ui` returns a short result, never the program, and never raises into the run."""

import json
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool

from genui.schema import SchemaError
from genui.tool import MAX_RESULT, build_render_ui
from permissions.rules import RulesEngine
from verify.gate import MUTATIONS

MARKER = "PROGRAM-MARKER-9f3a"


def payload(tool: StructuredTool, program: str) -> dict[str, object]:
    result = tool.invoke({"ui": program})
    assert isinstance(result, str)
    assert len(result) <= MAX_RESULT
    decoded: object = json.loads(result)
    assert isinstance(decoded, dict)
    return {str(key): value for key, value in decoded.items()}


def test_success_is_evidence_and_never_the_program() -> None:
    tool = build_render_ui()
    program = f'root = Stack([c])\nc = Callout("{MARKER}")'
    assert payload(tool, program) == {
        "ok": True,
        "components": ["Stack", "Callout"],
        "statements": 2,
    }
    echoed = tool.invoke({"ui": program})
    assert isinstance(echoed, str) and MARKER not in echoed


def test_failure_is_one_line_and_the_run_continues() -> None:
    result = payload(build_render_ui(), 'root = Stack([a])\na = Chart("x")')
    assert result == {"ok": False, "error": 'line 2: unknown component "Chart"'}
    assert len(str(result["error"])) <= 200


def test_a_broken_contract_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> None:
        raise SchemaError("missing")

    monkeypatch.setattr("genui.tool.library", broken)
    assert payload(build_render_ui(), "root = Stack([])") == {
        "ok": False,
        "error": "the rendering library is unavailable",
    }


def test_unknown_ids_create_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An id the run never produced renders the component's not-found state and nothing else."""
    monkeypatch.chdir(tmp_path)
    result = payload(
        build_render_ui(),
        'root = Stack([q])\nq = QuestionCard("run-never", "call-never")',
    )
    assert result["ok"] is True
    assert result["components"] == ["Stack", "QuestionCard"]
    assert list(tmp_path.iterdir()) == []


def test_rendering_is_not_a_mutation_for_the_verify_gate() -> None:
    assert "render_ui" not in MUTATIONS


@pytest.mark.parametrize("mode", ["read-only", "ask", "auto"])
def test_rendering_is_allowed_in_every_mode(tmp_path: Path, mode: str) -> None:
    engine = RulesEngine(tmp_path, mode)  # type: ignore[arg-type]
    outcome = engine.decide("render_ui")
    assert outcome.action == "allow"
    assert not any("render_ui" in item for item in engine.always_ask())


def test_an_over_long_program_is_rejected_by_the_tool_contract() -> None:
    tool = build_render_ui()
    with pytest.raises(Exception):
        tool.invoke({"ui": "x" * 20_001})
