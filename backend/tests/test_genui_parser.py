"""The bounded grammar: what it accepts, where it stops, and which line it blames."""

import pytest

from genui.parser import (
    MAX_CHARS,
    MAX_STATEMENTS,
    Array,
    Call,
    Literal,
    Object,
    ParseError,
    Reference,
    parse,
)


def test_statements_keep_their_line_numbers() -> None:
    program = parse('root = Stack([a])\na = Callout("hi")')
    assert [statement.name for statement in program.statements] == ["root", "a"]
    assert [statement.line for statement in program.statements] == [1, 2]
    assert program.root is not None
    assert isinstance(program.root.value, Call)


def test_references_arrays_and_objects() -> None:
    program = parse('root = Stack([a, [b]])\na = Callout("x")\nb = KeyValue("k", "v")')
    root = program.root
    assert root is not None and isinstance(root.value, Call)
    children = root.value.args[0]
    assert isinstance(children, Array)
    assert children.items[0] == Reference("a")
    assert isinstance(children.items[1], Array)


def test_strings_unescape_without_evaluating_anything() -> None:
    program = parse(r'root = Stack([c])' + "\n" + r'c = Callout("a\"b\\c\nd\u00e9")')
    statement = program.find("c")
    assert statement is not None and isinstance(statement.value, Call)
    assert statement.value.args[0] == Literal('a"b\\c\ndé')


def test_numbers_booleans_and_null_are_literals() -> None:
    program = parse("root = Stack([1, -2.5, 3e2, true, false, null])")
    root = program.root
    assert root is not None and isinstance(root.value, Call)
    values = root.value.args[0]
    assert isinstance(values, Array)
    assert [item.value if isinstance(item, Literal) else None for item in values.items] == [
        1,
        -2.5,
        300.0,
        True,
        False,
        None,
    ]


def test_objects_parse_with_string_keys() -> None:
    program = parse('root = Stack([{"a": [1, true], "b": null}])')
    root = program.root
    assert root is not None and isinstance(root.value, Call)
    children = root.value.args[0]
    assert isinstance(children, Array)
    entry = children.items[0]
    assert isinstance(entry, Object)
    assert [key for key, _ in entry.entries] == ["a", "b"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('root = Stack([c])\nc = Callout("open', "a string is not closed"),
        (r'root = Stack([c])' + "\n" + r'c = Callout("bad \q")', 'unknown escape "\\q"'),
        ("root = Stack([]) junk", "only one statement fits on a line"),
        ("root = Stack([1)", 'expected "]"'),
        ("root = Stack([)", "expected a value"),
        ("= Stack([])", 'expected "ident"'),
        ("root = Stack([c])\nc = Callout(@)", 'unexpected character "@"'),
        ("", "the program is empty"),
    ],
)
def test_a_broken_program_names_the_problem(text: str, message: str) -> None:
    with pytest.raises(ParseError) as caught:
        parse(text)
    assert message in str(caught.value)
    assert str(caught.value).startswith("line ")


def test_nesting_stops_at_the_limit() -> None:
    with pytest.raises(ParseError) as caught:
        parse("root = Stack(" + "[" * 9 + "]" * 9 + ")")
    assert "deeper than 8" in str(caught.value)


def test_the_statement_budget_is_enforced() -> None:
    body = "\n".join(f'a{index} = Callout("x")' for index in range(MAX_STATEMENTS + 1))
    with pytest.raises(ParseError) as caught:
        parse(f"root = Stack([])\n{body}")
    assert "at most" in str(caught.value)


def test_the_size_budget_is_enforced() -> None:
    with pytest.raises(ParseError) as caught:
        parse('root = Stack([])\nc = Callout("' + "x" * MAX_CHARS + '")')
    assert "characters" in str(caught.value)
