"""The `render_ui` tool: validate a program and return a short result, never the program.

Rendering is read-only. It writes no file, asks no question and grants nothing, so it is
allowed in every mode and is absent from the always-ask list.
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from genui.parser import MAX_CHARS
from genui.prompt import render_prompt
from genui.schema import LibrarySchema, SchemaError, library
from genui.validate import Problem, used_components, validate

MAX_RESULT = 500


class RenderInput(BaseModel):
    ui: str = Field(
        min_length=1,
        max_length=MAX_CHARS,
        description="One program in the rendering language; the library below defines it.",
    )


def _result(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))[:MAX_RESULT]


def build_render_ui(schema: LibrarySchema | None = None) -> StructuredTool:
    def render(ui: str) -> str:
        try:
            contract = schema or library()
        except SchemaError:
            return _result({"ok": False, "error": "the rendering library is unavailable"})
        checked = validate(ui, contract)
        if isinstance(checked, Problem):
            return _result({"ok": False, "error": str(checked)})
        return _result(
            {
                "ok": True,
                "components": used_components(checked),
                "statements": len(checked.statements),
            }
        )

    return StructuredTool.from_function(
        render,
        name="render_ui",
        description=render_prompt(),
        args_schema=RenderInput,
    )
