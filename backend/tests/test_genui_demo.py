"""The offline rendering run sends a real program, and the broken one is really rejected."""

from langchain_core.messages import ToolCall, ToolMessage

from genui.schema import library
from genui.validate import Problem, validate
from providers.genui_demo import BROKEN, demo_render


def first_call(task: str, locale: str = "fa") -> ToolCall:
    message = demo_render(task, [], locale)
    assert message is not None
    assert message.tool_calls
    call = message.tool_calls[0]
    assert call["name"] == "render_ui"
    return call


def test_the_demo_program_is_valid_in_both_languages() -> None:
    for locale in ("fa", "en"):
        call = first_call("demo render a summary", locale)
        assert not isinstance(validate(str(call["args"]["ui"]), library()), Problem)


def test_the_broken_program_fails_on_the_line_it_names() -> None:
    call = first_call("demo render bad")
    assert call["args"]["ui"] == BROKEN
    result = validate(BROKEN, library())
    assert isinstance(result, Problem)
    assert str(result) == 'line 2: unknown component "Chart"'


def test_the_run_continues_in_text_after_the_tool_answered() -> None:
    answered = [ToolMessage(content='{"ok": true}', tool_call_id="demo-render", name="render_ui")]
    for task in ("demo render a summary", "demo render bad"):
        message = demo_render(task, answered, "en")
        assert message is not None
        assert not message.tool_calls
        assert str(message.content).strip()


def test_an_unrelated_task_is_not_a_rendering_run() -> None:
    assert demo_render("demo edit a.txt: x => y", [], "fa") is None
