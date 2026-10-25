"""Every rejection is one line with the line number that caused it."""

from typing import Final

import pytest

from genui.parser import Program
from genui.schema import LibrarySchema, library
from genui.validate import Problem, used_components, validate

SCHEMA: Final[LibrarySchema] = library()


def problem(text: str) -> str:
    result = validate(text, SCHEMA)
    assert isinstance(result, Problem), f"expected a problem, got {result}"
    assert len(str(result)) <= 200
    return str(result)


def accepted(text: str) -> Program:
    result = validate(text, SCHEMA)
    assert isinstance(result, Program), f"expected a program, got {result}"
    return result


def test_a_complete_program_is_accepted() -> None:
    program = accepted(
        "root = Stack([summary, tabs])\n"
        'summary = Callout("Three files changed")\n'
        'tabs = Tabs(["Files", "Diff"], [tree, diff])\n'
        'tree = FileTree("run-1")\n'
        'diff = DiffView("-a\\n+b")\n'
    )
    assert used_components(program) == ["Stack", "Callout", "Tabs", "FileTree", "DiffView"]


def test_unknown_component_is_rejected_before_anything_renders() -> None:
    assert problem('root = Stack([a])\na = Chart("x")') == 'line 2: unknown component "Chart"'


def test_an_unknown_root_component_is_the_same_error() -> None:
    assert problem('root = Chart("x")') == 'line 1: unknown component "Chart"'


def test_wrong_arity_names_the_range() -> None:
    assert problem("root = Stack([c])\nc = Callout()") == "line 2: Callout takes 1 arguments, not 0"
    assert problem('root = Stack([c])\nc = Callout("a", "b")') == (
        "line 2: Callout takes 1 arguments, not 2"
    )


def test_a_literal_of_the_wrong_type_is_rejected() -> None:
    assert problem("root = Stack([c])\nc = Callout(1)") == 'line 2: "text" must be a string'


def test_an_unresolved_reference_is_rejected() -> None:
    assert problem("root = Stack([missing])") == 'line 1: "missing" is not defined'


def test_an_unreachable_statement_is_rejected() -> None:
    assert problem('root = Stack([])\nextra = Callout("x")') == 'line 2: "extra" is never used'


def test_duplicate_and_malformed_names_are_rejected() -> None:
    assert problem('root = Stack([])\na = Callout("x")\na = Callout("y")') == (
        'line 3: "a" is defined twice'
    )
    long_name = "a" * 65
    assert problem(f'root = Stack([])\n{long_name} = Callout("x")') == (
        f'line 2: "{long_name}" is not a valid name'
    )


def test_id_props_are_stricter_than_free_text() -> None:
    assert problem('root = Stack([q])\nq = QuestionCard("run 1", "c")') == (
        'line 2: "runId" must be an id like "abc-123"'
    )
    accepted('root = Stack([q])\nq = QuestionCard("run-1", "call_2")')


def test_a_tab_needs_one_panel_per_label() -> None:
    assert problem('root = Stack([t])\nt = Tabs(["A", "B"], [c])\nc = Callout("x")') == (
        "line 2: Tabs needs one panel per label (2 labels, 1 panels)"
    )


def test_an_inline_call_means_the_same_as_a_reference() -> None:
    accepted('root = Stack([Callout("inline")])')
    accepted('root = Stack([Table(["a"], [["1"]])])')
    assert problem('root = Stack([{"a": 1}])') == (
        'line 1: "children" must reference one of: '
        "Callout, KeyValue, Table, DiffView, FileTree, TerminalPanel, TestResults, "
        "ApprovalCard, QuestionCard, PlanChecklist, Stack, Tabs"
    )


def test_the_depth_and_size_bounds_fail_closed() -> None:
    assert problem("root = Stack(" + "[" * 9 + "]" * 9 + ")") == "line 1: nesting is deeper than 8"
    assert "characters" in problem('root = Stack([])\nc = Callout("' + "x" * 20_001 + '")')


def test_the_root_statement_is_required() -> None:
    assert problem('a = Callout("x")') == 'line 1: the program has no "root" statement'
    assert problem('root = "text"') == 'line 1: "root" must call Stack'


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_an_empty_program_is_a_problem_not_an_exception(text: str) -> None:
    assert problem(text) == "line 1: the program is empty"


MALFORMED = [
    "root = Stack([)",
    "root = Stack([[])",
    "root = Stack([c])\nc = Callout(",
    'root = Stack([c])\nc = Callout("unterminated)',
    "root = Stack([c])\nc = Callout('single')",
    "root = Stack([c])\nc = Callout(\"tab\there\")",
    "root = Stack([c])\nc = Callout(\u0000)",
    "root = Stack([" + "[" * 40 + "]" * 39 + "])",
    "root = Stack([])\n" + "\n".join(f"x{i} = Callout(\"a\")" for i in range(300)),
    "root = Stack([c])\nc = Callout(1e999999)",
    "root = Stack([c])\nc = Callout(-)",
    "root = Stack([c])\nc = Callout(\"\\u12\")",
    "root = Stack([c])\nc = Tabs([\"a\"], [c], [c])",
    "root=Stack([c])\nc=Callout(\"x\")=Callout(\"y\")",
]


@pytest.mark.parametrize("text", MALFORMED)
def test_malformed_input_never_raises(text: str) -> None:
    result = validate(text, SCHEMA)
    assert isinstance(result, (Program, Problem))
