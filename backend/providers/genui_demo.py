"""Offline `render_ui` runs: one valid program and one the validator must reject.

The walkthrough needs a real rendering attempt without a key or a network, so the demo sends
the same tool call a model would and then answers in one sentence. The broken variant proves
the failure path: the tool refuses it, the note carries the reason, and the run still finishes.
"""

import re

from langchain_core.messages import AIMessage, ToolMessage

RENDER = re.compile(r"demo render\b")

FA = (
    'root = Stack([title, facts, tabs])\n'
    'title = Callout("این اجرا سه فایل را تغییر داد و آزمون‌ها سبز است.")\n'
    'facts = Table(["فایل", "تغییر"], [["src/app/page.tsx", "ویرایش"], '
    '["src/lib/api.ts", "ویرایش"], ["README.md", "افزودن"]])\n'
    'tabs = Tabs(["خلاصه", "قدم بعدی"], [check, next_step])\n'
    'check = Callout("هیچ فرمانی نیمه‌کاره نماند.")\n'
    'next_step = KeyValue("پیشنهاد", "اجرای آزمون‌های کامل")\n'
)
EN = (
    'root = Stack([title, facts, tabs])\n'
    'title = Callout("This run changed three files and the tests pass.")\n'
    'facts = Table(["File", "Change"], [["src/app/page.tsx", "edited"], '
    '["src/lib/api.ts", "edited"], ["README.md", "added"]])\n'
    'tabs = Tabs(["Summary", "Next step"], [check, next_step])\n'
    'check = Callout("No command was left half-run.")\n'
    'next_step = KeyValue("Suggestion", "Run the full test suite")\n'
)
BROKEN = 'root = Stack([chart])\nchart = Chart("trend")\n'
"""`Chart` is not in the library, so the engine must refuse this on line 2."""


def program(locale: str) -> str:
    return EN if locale == "en" else FA


def demo_render(task: str, results: list[ToolMessage], locale: str = "fa") -> AIMessage | None:
    """Return the next scripted turn, or `None` when this is not a rendering run."""
    if not RENDER.match(task):
        return None
    broken = "bad" in task
    if not any(message.name == "render_ui" for message in results):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "render_ui",
                    "id": "demo-render",
                    "args": {"ui": BROKEN if broken else program(locale)},
                }
            ],
        )
    if broken:
        text = (
            "I could not draw the chart; the note carries the line that failed."
            if locale == "en"
            else "نمودار را نتوانستم بکشم؛ یادداشت، خطای همان خط را نشان می‌دهد."
        )
    else:
        text = (
            "The interface above is the program the engine validated."
            if locale == "en"
            else "رابط بالا همان برنامه‌ای است که موتور تأیید کرد."
        )
    return AIMessage(content=text)
