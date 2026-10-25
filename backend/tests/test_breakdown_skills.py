"""The breakdown's five rows add up, and skills and memory are their own rows."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately

from verify.context import Window, breakdown


def test_an_empty_prompt_is_all_zero() -> None:
    found = breakdown([])
    assert found.messages == 0
    assert found.skills == 0
    assert found.memory == 0


def test_skills_and_memory_are_measured_from_their_blocks() -> None:
    skills = "Skills (call load_skill with a name to read its full instructions):\n- a: b"
    memory = "Workspace memory (written by the person):\nUse ruff."
    system = f"You are CodeHarness.\n\n{skills}\n\n{memory}\n\nUI library."
    found = breakdown([], system, [], skills, memory)
    assert found.skills > 0
    assert found.memory > 0
    assert found.system > 0


def test_the_rows_do_not_double_count() -> None:
    skills = "Skills:\n- a: b"
    memory = "Workspace memory:\nUse ruff."
    full = f"You are CodeHarness.\n\n{skills}\n\n{memory}"
    found = breakdown([], full, [], skills, memory)
    direct = count_tokens_approximately([SystemMessage(content=full)])
    # The three rows are a partition of one measurement, not three measurements.
    assert found.system + found.skills + found.memory == direct
    assert found.system < direct


def test_the_window_passes_its_blocks_through() -> None:
    window = Window(system="prompt", skills="Skills:\n- a: b", memory="Workspace memory:\nx")
    found = window.breakdown()
    assert found.skills > 0
    assert found.memory > 0
    assert window.skills.startswith("Skills:")


def test_messages_and_tool_results_stay_separate() -> None:
    messages = [SystemMessage(content="system"), HumanMessage(content="hello there")]
    found = breakdown(messages, "", [])
    assert found.messages > 0
    assert found.tool_results == 0
