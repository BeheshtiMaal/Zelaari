"""The library contract, read from the generated JSON schema.

`src/genui/library.tsx` is the only definition of the library. `npm run generate:genui` writes
the prompt the model reads and the schema this module validates against, so the two cannot
drift: there is no second, hand-written component list in Python.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "agent" / "genui_schema.json"

ROOT = "Stack"
"""The entry point every program must define. `test_genui_prompt` ties this to the prompt."""

ID_PROPS = frozenset({"runId", "callId", "approvalId", "planId", "revision"})
"""Props that name engine state. They are matched against a stricter shape than free text."""

ShapeKind = Literal["string", "number", "boolean", "null", "refs", "array", "object", "any"]


class SchemaError(RuntimeError):
    """The generated contract is missing or unreadable, so nothing may be rendered."""


@dataclass(frozen=True)
class Shape:
    kind: ShapeKind
    refs: tuple[str, ...] = ()
    element: Shape | None = None
    properties: tuple[tuple[str, Shape], ...] = ()

    @property
    def is_id(self) -> bool:
        return self.kind == "string"


@dataclass(frozen=True)
class Prop:
    name: str
    required: bool
    shape: Shape

    @property
    def is_id(self) -> bool:
        return self.name in ID_PROPS and self.shape.kind == "string"


@dataclass(frozen=True)
class Component:
    name: str
    description: str
    props: tuple[Prop, ...]

    @property
    def required(self) -> int:
        return sum(1 for prop in self.props if prop.required)

    def prop(self, name: str) -> Prop | None:
        return next((prop for prop in self.props if prop.name == name), None)


@dataclass(frozen=True)
class LibrarySchema:
    components: dict[str, Component]

    def get(self, name: str) -> Component | None:
        return self.components.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self.components)


def _shape(value: object) -> Shape:
    if not isinstance(value, dict):
        return Shape("any")
    any_of = value.get("anyOf")
    if isinstance(any_of, list):
        refs = tuple(
            str(entry["$ref"]).rsplit("/", 1)[-1]
            for entry in any_of
            if isinstance(entry, dict) and isinstance(entry.get("$ref"), str)
        )
        return Shape("refs", refs=refs) if refs else Shape("any")
    kind = value.get("type")
    if kind == "array":
        return Shape("array", element=_shape(value.get("items")))
    if kind == "object":
        properties = value.get("properties")
        fields = (
            tuple((str(name), _shape(spec)) for name, spec in properties.items())
            if isinstance(properties, dict)
            else ()
        )
        return Shape("object", properties=fields)
    if kind in {"string", "number", "boolean", "null"}:
        return Shape(kind)  # narrowed by the membership test above
    return Shape("any")


def parse(payload: object) -> LibrarySchema:
    if not isinstance(payload, dict):
        raise SchemaError("The generated schema is not an object")
    properties = payload.get("properties")
    defs = payload.get("$defs")
    if not isinstance(properties, dict) or not isinstance(defs, dict):
        raise SchemaError("The generated schema has no components")
    components: dict[str, Component] = {}
    for name in properties:
        definition = defs.get(name)
        if not isinstance(definition, dict):
            raise SchemaError(f"The generated schema is missing {name}")
        fields = definition.get("properties")
        fields = fields if isinstance(fields, dict) else {}
        required = set(definition.get("required") or [])
        components[name] = Component(
            name=name,
            description=str(definition.get("description", "")),
            props=tuple(
                Prop(name=str(prop), required=str(prop) in required, shape=_shape(spec))
                for prop, spec in fields.items()
            ),
        )
    if ROOT not in components:
        raise SchemaError(f"The generated schema has no root component {ROOT}")
    return LibrarySchema(components)


@lru_cache(maxsize=1)
def library() -> LibrarySchema:
    """Loaded once per process; a missing or broken contract fails closed."""
    try:
        payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SchemaError(f"The generated schema is unreadable: {error}") from error
    return parse(payload)
