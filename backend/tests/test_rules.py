"""Rules precedence, the mode ceiling and the always-ask list."""

from pathlib import Path

import pytest

from permissions.rules import RulesEngine
from permissions.types import RulesFile


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / ".harness").mkdir()
    return tmp_path


def engine(root: Path, mode: str = "ask", tools: dict | None = None) -> RulesEngine:
    rules = RulesFile.model_validate({"mode": mode, "tools": tools or {}})
    return RulesEngine(root, mode=mode, rules=rules)  # type: ignore[arg-type]


def test_mode_defaults() -> None:
    root = Path("C:/work")
    assert engine(root, "ask").decide("read_file", path="a.txt").action == "allow"
    assert engine(root, "ask").decide("write_file", path="a.txt").action == "ask"
    assert engine(root, "ask").decide("delete", path="a.txt").action == "ask"
    assert engine(root, "ask").decide("run_command", command="npm test").action == "ask"
    assert engine(root, "auto").decide("write_file", path="a.txt").action == "allow"
    assert engine(root, "auto").decide("run_command", command="npm test").action == "allow"
    assert engine(root, "read-only").decide("write_file", path="a.txt").action == "deny"


def test_most_specific_rule_wins(root: Path) -> None:
    rules = {
        "write_file": [
            {"glob": "*", "action": "ask"},
            {"glob": "src/**", "action": "allow"},
        ]
    }
    subject = engine(root, "ask", rules)
    assert subject.decide("write_file", path="src/parser.py").action == "allow"
    assert subject.decide("write_file", path="docs/readme.md").action == "ask"


def test_ties_resolve_to_the_most_restrictive(root: Path) -> None:
    rules = {
        "write_file": [
            {"glob": "src/**", "action": "allow"},
            {"glob": "src/**", "action": "deny"},
        ]
    }
    assert engine(root, "auto", rules).decide("write_file", path="src/a.py").action == "deny"


def test_glob_matching_is_case_insensitive(root: Path) -> None:
    rules = {"write_file": [{"glob": "SRC/**", "action": "allow"}]}
    assert engine(root, "ask", rules).decide("write_file", path="src/A.py").action == "allow"


def test_malformed_rules_fail_closed(root: Path) -> None:
    (root / ".harness" / "rules.json").write_text("{not json", encoding="utf-8")
    subject = RulesEngine.load(root, "auto")
    assert subject.load_error is not None
    assert subject.decide("write_file", path="a.txt").action == "ask"
    assert subject.decide("run_command", command="npm test").action == "ask"


def test_unreadable_rules_still_deny_in_read_only(root: Path) -> None:
    (root / ".harness" / "rules.json").write_text("[]", encoding="utf-8")
    subject = RulesEngine.load(root, "read-only")
    assert subject.load_error is not None
    assert subject.decide("write_file", path="a.txt").action == "deny"


def test_auto_still_asks_for_engine_storage(root: Path) -> None:
    subject = engine(root, "auto")
    outcome = subject.decide("write_file", path=".harness/rules.json")
    assert outcome.action == "ask"
    assert "engine storage" in outcome.reason


def test_auto_still_asks_for_high_risk_commands(root: Path) -> None:
    subject = engine(root, "auto")
    outcome = subject.decide("run_command", command="git push --force")
    assert outcome.action == "ask"
    assert outcome.risk.level == "high"
    assert outcome.risk.reasons


def test_auto_still_asks_for_web_queries(root: Path) -> None:
    assert engine(root, "auto").decide("web_search").action == "ask"


def test_auto_allows_an_ordinary_command(root: Path) -> None:
    outcome = engine(root, "auto").decide("run_command", command="npm test")
    assert outcome.action == "allow"
    assert outcome.risk.level == "low"


def test_explicit_allow_rule_escapes_always_ask(root: Path) -> None:
    rules = {"write_file": [{"glob": ".harness/rules.json", "action": "allow"}]}
    assert (
        engine(root, "auto", rules).decide("write_file", path=".harness/rules.json").action
        == "allow"
    )


def test_read_only_denies_even_with_an_allow_rule(root: Path) -> None:
    rules = {"write_file": [{"glob": "**", "action": "allow"}]}
    assert engine(root, "read-only", rules).decide("write_file", path="src/a.py").action == "deny"


def test_deny_rule_beats_default_allow(root: Path) -> None:
    rules = {"read_file": [{"glob": "secrets/**", "action": "deny"}]}
    subject = engine(root, "ask", rules)
    assert subject.decide("read_file", path="secrets/token.txt").action == "deny"
    assert subject.decide("read_file", path="src/a.py").action == "allow"


def test_save_and_reload_round_trip(root: Path) -> None:
    subject = engine(root, "ask")
    subject.save(
        RulesFile(mode="auto", tools={"write_file": [{"glob": "src/**", "action": "allow"}]})
    )
    reloaded = RulesEngine.load(root, None)
    assert reloaded.mode == "auto"
    assert reloaded.decide("write_file", path="src/a.py").action == "allow"


def test_traversal_in_a_rule_glob_is_rejected() -> None:
    with pytest.raises(ValueError):
        RulesFile.model_validate({"tools": {"read_file": [{"glob": "../*", "action": "allow"}]}})
