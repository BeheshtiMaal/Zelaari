"""The shipped content is real: five bundled skills and one example project skill."""

from pathlib import Path

import pytest

from skills import loader
from skills.types import SkillRecord, SkillsState

REPO = Path(__file__).resolve().parents[2]
EXPECTED = {
    "feature-spec": "/spec",
    "fix-failing-tests": "/fix",
    "grill-me": "/grill",
    "python-project": None,
    "web-search": "/search",
}


@pytest.fixture
def bundled(monkeypatch: pytest.MonkeyPatch) -> list[SkillRecord]:
    monkeypatch.setenv(loader.BUNDLED_ENV, str(REPO / "skills"))
    return loader.discover(None, None)


def test_the_five_bundled_skills(bundled: list[SkillRecord]) -> None:
    assert sorted(record.name for record in bundled) == sorted(EXPECTED)


def test_each_skill_is_clean_and_complete(bundled: list[SkillRecord]) -> None:
    for record in bundled:
        assert record.problem is None
        assert record.enabled is True
        assert record.scan.status == "clean"
        assert record.command == EXPECTED[record.name]
        assert 1 <= record.tokens <= 200
        assert len(record.description) <= 1024


def test_the_web_skill_requires_approval(bundled: list[SkillRecord]) -> None:
    web = next(record for record in bundled if record.name == "web-search")
    assert web.requires_approval is True
    assert web.category == "web"


def test_bodies_are_real_instructions(bundled: list[SkillRecord]) -> None:
    for record in bundled:
        detail = loader.detail(record, None, None)
        assert detail.body.startswith("# "), record.name
        assert 8 <= len(detail.body.splitlines()) <= 200
        assert len(detail.body) < 32_000


def test_the_example_project_skill_is_off_by_default() -> None:
    space = REPO / "examples" / "sample-project"
    found = loader.discover(space, None, SkillsState())
    # The project skill joins the five bundled ones; it is the workspace one.
    assert len(found) == 6
    record = next(item for item in found if item.name == "read-framework-docs")
    assert record.source == "workspace"
    assert record.enabled is False
    assert record.problem is None
    assert record.scan.status == "clean"
