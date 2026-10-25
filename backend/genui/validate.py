"""Schema-driven validation. The first failure becomes one line with its line number.

Every check is driven by the generated contract, so a component the library does not declare
cannot render, and a prop the library does not declare cannot be passed. Nothing here
evaluates, executes or imports anything the program names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from genui.parser import (
    Array,
    Call,
    Literal,
    Node,
    Object,
    ParseError,
    Program,
    Reference,
    parse,
)
from genui.schema import ID_PROPS, ROOT, Component, LibrarySchema, Shape

ID_VALUE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
MAX_ERROR = 200
POSITIONAL_PAIRS = ("labels", "panels")
"""Props that must agree in length because they are read position by position."""


@dataclass(frozen=True)
class Problem:
    line: int
    message: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.message}"[:MAX_ERROR]


class _Invalid(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(message)
        self.line = line
        self.message = message


def validate(text: str, schema: LibrarySchema) -> Program | Problem:
    """Return the checked program, or the one line that explains why it cannot render."""
    try:
        program = parse(text)
        _check(program, schema)
    except ParseError as error:
        return Problem(error.line, error.message)
    except _Invalid as error:
        return Problem(error.line, error.message)
    except Exception:  # the tool must never raise into the run
        return Problem(1, "the program could not be read")
    return program


def used_components(program: Program) -> list[str]:
    """Component names the program actually calls, in first-use order."""
    found: list[str] = []

    def walk(node: Node) -> None:
        if isinstance(node, Call):
            if node.name not in found:
                found.append(node.name)
            for arg in node.args:
                walk(arg)
        elif isinstance(node, Array):
            for item in node.items:
                walk(item)
        elif isinstance(node, Object):
            for _, value in node.entries:
                walk(value)

    for statement in program.statements:
        walk(statement.value)
    return found


def _check(program: Program, schema: LibrarySchema) -> None:
    declared = {statement.name for statement in program.statements}
    seen: set[str] = set()
    for statement in program.statements:
        if statement.name in seen:
            raise _Invalid(statement.line, f'"{statement.name}" is defined twice')
        seen.add(statement.name)
        if not NAME.fullmatch(statement.name):
            raise _Invalid(statement.line, f'"{statement.name}" is not a valid name')

    root = program.root
    if root is None:
        raise _Invalid(1, 'the program has no "root" statement')
    if not isinstance(root.value, Call):
        raise _Invalid(root.line, f'"root" must call {ROOT}')
    if schema.get(root.value.name) is None:
        raise _Invalid(root.line, f'unknown component "{root.value.name}"')
    if root.value.name != ROOT:
        raise _Invalid(root.line, f'"root" must call {ROOT}, not "{root.value.name}"')

    for statement in program.statements:
        _node(statement.value, schema, declared, statement.line)

    reachable = _reachable(program)
    for statement in program.statements:
        if statement.name != "root" and statement.name not in reachable:
            raise _Invalid(statement.line, f'"{statement.name}" is never used')


def _node(node: Node, schema: LibrarySchema, declared: set[str], line: int) -> None:
    if isinstance(node, Reference):
        if node.name not in declared:
            raise _Invalid(line, f'"{node.name}" is not defined')
        return
    if isinstance(node, Array):
        for item in node.items:
            _node(item, schema, declared, line)
        return
    if isinstance(node, Object):
        for _, value in node.entries:
            _node(value, schema, declared, line)
        return
    if isinstance(node, Call):
        component = schema.get(node.name)
        if component is None:
            raise _Invalid(line, f'unknown component "{node.name}"')
        if not component.required <= len(node.args) <= len(component.props):
            raise _Invalid(
                line, f"{node.name} takes {_arity(component)} arguments, not {len(node.args)}"
            )
        for prop, argument in zip(component.props, node.args, strict=False):
            _arg(argument, prop.shape, prop.name, schema, declared, line)
        _pair(component, node, line)


def _arg(
    node: Node,
    shape: Shape,
    name: str,
    schema: LibrarySchema,
    declared: set[str],
    line: int,
) -> None:
    if shape.kind == "refs":
        if isinstance(node, Reference):
            if node.name not in declared:
                raise _Invalid(line, f'"{node.name}" is not defined')
            return
        if isinstance(node, Call) and node.name in shape.refs:
            _node(node, schema, declared, line)
            return
        raise _Invalid(line, f'"{name}" must reference one of: {", ".join(shape.refs)}')
    if shape.kind == "array":
        if not isinstance(node, Array):
            raise _Invalid(line, f'"{name}" must be an array')
        for item in node.items:
            _arg(item, shape.element or Shape("any"), name, schema, declared, line)
        return
    if shape.kind == "object":
        if not isinstance(node, Object):
            raise _Invalid(line, f'"{name}" must be an object')
        return
    if not isinstance(node, Literal):
        raise _Invalid(line, f'"{name}" must be a literal value')
    if name in ID_PROPS and shape.kind == "string":
        if not isinstance(node.value, str) or not ID_VALUE.fullmatch(node.value):
            raise _Invalid(line, f'"{name}" must be an id like "abc-123"')
    if not _literal_matches(node.value, shape.kind):
        raise _Invalid(line, f'"{name}" must be a {shape.kind}')


def _literal_matches(value: str | int | float | bool | None, kind: str) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    return True


def _arity(component: Component) -> str:
    total = len(component.props)
    required = component.required
    return str(total) if required == total else f"{required} to {total}"


def _pair(component: Component, call: Call, line: int) -> None:
    """Two positional arrays must be the same length, or a tab would have no panel."""
    lengths: list[int] = []
    for name in POSITIONAL_PAIRS:
        index = next((i for i, prop in enumerate(component.props) if prop.name == name), None)
        if index is None or index >= len(call.args):
            return
        argument = call.args[index]
        if not isinstance(argument, Array):
            return
        lengths.append(len(argument.items))
    if len(lengths) == 2 and lengths[0] != lengths[1]:
        raise _Invalid(
            line,
            f"{component.name} needs one panel per label "
            f"({lengths[0]} labels, {lengths[1]} panels)",
        )


def _reachable(program: Program) -> set[str]:
    values = {statement.name: statement.value for statement in program.statements}
    reachable: set[str] = set()

    def walk(node: Node) -> None:
        if isinstance(node, Reference):
            if node.name in values and node.name not in reachable:
                reachable.add(node.name)
                walk(values[node.name])
        elif isinstance(node, Call):
            for arg in node.args:
                walk(arg)
        elif isinstance(node, Array):
            for item in node.items:
                walk(item)
        elif isinstance(node, Object):
            for _, value in node.entries:
                walk(value)

    walk(values["root"])
    return reachable
