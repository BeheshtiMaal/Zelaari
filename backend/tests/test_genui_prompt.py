"""The description is the generated library plus a bounded preamble, and it cannot drift."""

from pathlib import Path

import pytest

from genui.prompt import MAX_PROMPT, PREAMBLE, render_prompt
from genui.schema import ROOT, library


def test_the_description_names_every_component_and_stays_inside_the_budget() -> None:
    text = render_prompt()
    assert 0 < len(text) <= MAX_PROMPT
    for name in library().names():
        assert f"{name}(" in text, f"the description does not name {name}"
    assert text.startswith(PREAMBLE)


def test_the_root_component_matches_the_prompt() -> None:
    assert f"root = {ROOT}(" in render_prompt()


def test_the_preamble_states_the_rules_the_signatures_cannot() -> None:
    assert "render_ui" in PREAMBLE
    assert "ids that appear" in PREAMBLE
    assert "Never repeat the program" in PREAMBLE
    assert "secret" in PREAMBLE


def test_a_missing_prompt_still_yields_a_usable_description(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("genui.prompt.PROMPT_PATH", tmp_path / "absent.txt")
    assert render_prompt() == PREAMBLE
