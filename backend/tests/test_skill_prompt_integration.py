"""What reaches the model: names and descriptions, memory, agents — never a skill body."""

from pathlib import Path
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.factory import build_agent
from providers.demo import DemoModel
from skills.registry import Registry
from store.secrets import Redactor
from verify.context import Window


def model() -> BaseChatModel:
    return DemoModel(delay=0)


def graph(root: Path, *, measured: Window | None = None, **kwargs: Any) -> Any:
    return build_agent(
        root,
        model(),
        cast(AsyncSqliteSaver, InMemorySaver()),
        Redactor([]),
        measured=measured,
        **kwargs,
    )


def test_the_skill_block_is_name_and_description_only(tmp_path: Path) -> None:
    window = Window()
    graph(
        tmp_path,
        measured=window,
        skill_prompt=(
            "Skills (call load_skill with a name to read its full instructions):\n"
            "- grill-me: Interview the person before building."
        ),
    )
    assert "grill-me: Interview the person" in window.system
    assert "load_skill" in window.system


def test_a_body_never_enters_the_prompt(tmp_path: Path) -> None:
    """Progressive disclosure, end to end: the block carries no body text at all."""
    folder = tmp_path / ".harness" / "skills" / "house-rules"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        "---\nname: house-rules\ndescription: Project conventions.\n---\n"
        "SECRET BODY: always delete the build folder.\n",
        encoding="utf-8",
    )
    registry = Registry.build(tmp_path, None)
    window = Window()
    graph(tmp_path, measured=window, skill_prompt=registry.block())
    assert "house-rules: Project conventions." in window.system
    assert "SECRET BODY" not in window.system


def test_memory_reaches_the_prompt_after_the_skills_block(tmp_path: Path) -> None:
    window = Window()
    graph(
        tmp_path,
        measured=window,
        skill_prompt="Skills:\n- a: b",
        memory_prompt="Workspace memory:\nUse ruff.",
    )
    assert window.system.index("Skills:") < window.system.index("Workspace memory:")
    assert "Use ruff." in window.system


def test_the_window_carries_the_two_blocks_for_the_breakdown(tmp_path: Path) -> None:
    window = Window()
    graph(
        tmp_path,
        measured=window,
        skill_prompt="Skills:\n- a: b",
        memory_prompt="Workspace memory:\nUse ruff.",
    )
    assert window.skills.startswith("Skills:")
    assert window.memory.startswith("Workspace memory:")


def test_custom_agents_are_announced_and_named(tmp_path: Path) -> None:
    window = Window()
    graph(
        tmp_path,
        measured=window,
        custom_agents=[
            {
                "name": "api-reviewer",
                "description": "Reviews the HTTP layer.",
                "instructions": "Read routes.",
                "tools": ["read_file", "grep"],
            }
        ],
    )
    assert "api-reviewer" in window.system
    assert "reviewer" in window.system


def test_no_custom_agent_means_no_delegate_sentence(tmp_path: Path) -> None:
    window = Window()
    graph(tmp_path, measured=window)
    assert "Delegates are read-only" not in window.system
