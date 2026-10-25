"""Progressive disclosure: the prompt carries a name and a description, never a body."""

from typing import Any

from skills.prompt import (
    MAX_BLOCK,
    MAX_MEMORY,
    activated,
    activation_message,
    commands,
    estimate_tokens,
    memory_block,
    skills_block,
    summary_line,
    task_of,
)
from skills.types import SkillRecord, SkillsState


def record(name: str, description: str = "Does a thing.", **update: Any) -> SkillRecord:
    return SkillRecord(name=name, description=description, **update)


def test_only_name_and_description_reach_the_prompt() -> None:
    body = "SECRET BODY TEXT that must never be in the prompt"
    skill = record("grill-me", "Interview until specified.", command="/grill")
    block = skills_block([skill])
    assert "grill-me" in block
    assert "Interview until specified." in block
    assert body not in block
    assert "/grill" not in block


def test_the_block_is_bounded_and_truncates() -> None:
    skills = [record(f"skill-{index:03}", "x" * 160) for index in range(100)]
    block = skills_block(skills)
    assert len(block) <= MAX_BLOCK
    assert block.endswith("…")


def test_disabled_and_broken_skills_are_absent() -> None:
    block = skills_block(
        [
            record("on"),
            record("off", enabled=False),
            record("broken", problem="description is required"),
        ]
    )
    assert "- on:" in block
    assert "off" not in block
    assert "broken" not in block
    assert skills_block([record("off", enabled=False)]) == ""


def test_descriptions_are_collapsed_and_cut() -> None:
    line = summary_line("x", "a\n\nb   c")
    assert line == "- x: a b c"
    assert len(summary_line("x", "y" * 400)) <= 200


def test_commands_are_unique_and_enabled_only() -> None:
    found = commands(
        [
            record("one", command="/one"),
            record("two", command="/one"),
            record("three", command="/three", enabled=False),
            record("four", command=None),
        ]
    )
    assert [item.command for item in found] == ["/one"]
    assert found[0].name == "one"


def test_activation_matches_the_command() -> None:
    skills = [record("web-search", command="/search")]
    assert activated("/search", skills) is not None
    assert activated("/nope", skills) is None


def test_memory_block_is_bounded() -> None:
    assert memory_block("   ") == ""
    block = memory_block("z" * (MAX_MEMORY + 100))
    assert len(block) < MAX_MEMORY + 200
    assert block.endswith("…")


def test_token_estimate_is_stable() -> None:
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 8) == 2
    assert estimate_tokens("a" * 9) == 3


def test_state_defaults() -> None:
    assert SkillsState().overrides == {}
    assert SkillsState().catalog_url is None


def test_the_activation_envelope_keeps_the_persons_words() -> None:
    message = activation_message("/spec", "feature-spec", "Write three files.", "plan the cache")
    assert message.startswith("[harness] /spec activated the feature-spec skill.")
    assert "Write three files." in message
    assert task_of(message) == "plan the cache"


def test_a_plain_task_is_unchanged() -> None:
    assert task_of("fix the parser") == "fix the parser"
    assert task_of("[harness] but not an envelope") == "[harness] but not an envelope"


def test_a_body_containing_the_separator_still_yields_the_task() -> None:
    body = "Step one\n\n---\n\nStep two"
    message = activation_message("/x", "x", body, "the real task")
    assert task_of(message) == "the real task"
