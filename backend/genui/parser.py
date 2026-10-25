"""A bounded tokeniser and recursive-descent parser for the rendering language.

The grammar is deliberately small: statements are `identifier = expression`, and an expression
is a string, number, boolean, null, array, object, reference or component call with positional
arguments. Nothing is evaluated and nothing is executed — the parser only builds a tree, and it
refuses input that is too large, too deep or too long before it builds anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 20_000
MAX_STATEMENTS = 200
MAX_DEPTH = 8
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_PUNCTUATION = "=(),[]{}:"


class ParseError(Exception):
    """One line of explanation with the 1-based line it was found on."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


@dataclass(frozen=True)
class Literal:
    value: str | int | float | bool | None


@dataclass(frozen=True)
class Reference:
    name: str


@dataclass(frozen=True)
class Array:
    items: tuple[Node, ...]


@dataclass(frozen=True)
class Object:
    entries: tuple[tuple[str, Node], ...]


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Node, ...]


Node = Literal | Reference | Array | Object | Call


@dataclass(frozen=True)
class Statement:
    name: str
    value: Node
    line: int


@dataclass(frozen=True)
class Program:
    statements: tuple[Statement, ...]

    def find(self, name: str) -> Statement | None:
        return next((item for item in self.statements if item.name == name), None)

    @property
    def root(self) -> Statement | None:
        return self.find("root")


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    line: int


def _tokenise(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    index, line = 0, 1
    while index < len(text):
        char = text[index]
        if char in " \t\r":
            index += 1
        elif char == "\n":
            tokens.append(_Token("newline", "\n", line))
            line += 1
            index += 1
        elif char == '"':
            value, index = _read_string(text, index, line)
            tokens.append(_Token("string", value, line))
        elif char == "-" or char.isdigit():
            match = _NUMBER.match(text, index)
            if match is None or match.end() == index:
                raise ParseError(line, "a number is not formed correctly")
            tokens.append(_Token("number", match.group(), line))
            index = match.end()
        elif char.isalpha() or char == "_":
            start = index
            while index < len(text) and (text[index].isalnum() or text[index] == "_"):
                index += 1
            tokens.append(_Token("ident", text[start:index], line))
        elif char in _PUNCTUATION:
            tokens.append(_Token("punct", char, line))
            index += 1
        else:
            raise ParseError(line, f'unexpected character "{char}"')
    tokens.append(_Token("eof", "", line))
    return tokens


def _read_string(text: str, index: int, line: int) -> tuple[str, int]:
    start = line
    index += 1
    out: list[str] = []
    while index < len(text):
        char = text[index]
        if char == '"':
            return "".join(out), index + 1
        if char == "\n":
            break
        if char == "\\":
            index += 1
            if index >= len(text):
                break
            marker = text[index]
            if marker == "u":
                digits = text[index + 1 : index + 5]
                valid = len(digits) == 4 and all(
                    digit in "0123456789abcdefABCDEF" for digit in digits
                )
                if not valid:
                    raise ParseError(start, "a \\u escape needs four hex digits")
                out.append(chr(int(digits, 16)))
                index += 5
                continue
            if marker not in _ESCAPES:
                raise ParseError(start, f'unknown escape "\\{marker}"')
            out.append(_ESCAPES[marker])
            index += 1
            continue
        out.append(char)
        index += 1
    raise ParseError(start, "a string is not closed")


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.at = 0

    @property
    def token(self) -> _Token:
        return self.tokens[self.at]

    def advance(self) -> _Token:
        token = self.tokens[self.at]
        self.at += 1
        return token

    def skip_newlines(self) -> None:
        while self.token.kind == "newline":
            self.at += 1

    def expect(self, kind: str, value: str | None = None) -> _Token:
        token = self.token
        if token.kind != kind or (value is not None and token.value != value):
            raise ParseError(token.line, f'expected "{value or kind}"')
        return self.advance()

    def program(self) -> Program:
        statements: list[Statement] = []
        self.skip_newlines()
        while self.token.kind != "eof":
            name = self.expect("ident", None)
            self.expect("punct", "=")
            value = self.expression(0)
            if self.token.kind not in {"newline", "eof"}:
                raise ParseError(self.token.line, "only one statement fits on a line")
            statements.append(Statement(name=name.value, value=value, line=name.line))
            if len(statements) > MAX_STATEMENTS:
                raise ParseError(name.line, f"a program has at most {MAX_STATEMENTS} statements")
            self.skip_newlines()
        return Program(statements=tuple(statements))

    def expression(self, depth: int) -> Node:
        if depth > MAX_DEPTH:
            raise ParseError(self.token.line, f"nesting is deeper than {MAX_DEPTH}")
        token = self.token
        if token.kind == "string":
            return Literal(self.advance().value)
        if token.kind == "number":
            return Literal(_number(self.advance().value))
        if token.kind == "punct" and token.value == "[":
            return self.array(depth)
        if token.kind == "punct" and token.value == "{":
            return self.object(depth)
        if token.kind == "ident":
            self.advance()
            if token.value in {"true", "false"}:
                return Literal(token.value == "true")
            if token.value == "null":
                return Literal(None)
            if self.token.kind == "punct" and self.token.value == "(":
                return self.call(token.value, depth)
            return Reference(token.value)
        raise ParseError(token.line, "expected a value")

    def array(self, depth: int) -> Array:
        self.expect("punct", "[")
        items: list[Node] = []
        if not (self.token.kind == "punct" and self.token.value == "]"):
            while True:
                items.append(self.expression(depth + 1))
                if self.token.kind == "punct" and self.token.value == ",":
                    self.advance()
                    continue
                break
        self.expect("punct", "]")
        return Array(items=tuple(items))

    def object(self, depth: int) -> Object:
        self.expect("punct", "{")
        entries: list[tuple[str, Node]] = []
        if not (self.token.kind == "punct" and self.token.value == "}"):
            while True:
                key = self.expect("string", None)
                self.expect("punct", ":")
                entries.append((key.value, self.expression(depth + 1)))
                if self.token.kind == "punct" and self.token.value == ",":
                    self.advance()
                    continue
                break
        self.expect("punct", "}")
        return Object(entries=tuple(entries))

    def call(self, name: str, depth: int) -> Call:
        self.expect("punct", "(")
        args: list[Node] = []
        if not (self.token.kind == "punct" and self.token.value == ")"):
            while True:
                args.append(self.expression(depth + 1))
                if self.token.kind == "punct" and self.token.value == ",":
                    self.advance()
                    continue
                break
        self.expect("punct", ")")
        return Call(name=name, args=tuple(args))


def _number(text: str) -> int | float:
    return float(text) if any(mark in text for mark in ".eE") else int(text)


def parse(text: str) -> Program:
    """Parse a program, or raise `ParseError` with the line that failed."""
    if not text.strip():
        raise ParseError(1, "the program is empty")
    if len(text) > MAX_CHARS:
        raise ParseError(1, f"a program has at most {MAX_CHARS} characters")
    return _Parser(_tokenise(text)).program()
