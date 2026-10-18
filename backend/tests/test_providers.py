import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from providers.demo import DemoModel
from providers.openai_compat import configured_model


def test_demo_binds_tools_and_summarizes_actual_result() -> None:
    model = DemoModel()
    assert model.bind_tools([]) is model
    first = model.invoke([HumanMessage(content="read src/a.txt")])
    assert first.tool_calls[0]["args"] == {"file_path": "src/a.txt"}
    answer = model.invoke([ToolMessage(content="Real fixture content", tool_call_id="demo-read")])
    assert "Real fixture content" in str(answer.content)
    assert "Stack" in str(answer.content)


def test_provider_requires_explicit_config(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError):
        configured_model()
    monkeypatch.setenv("CODEHARNESS_API_KEY", "synthetic-provider-canary")
    monkeypatch.setenv("CODEHARNESS_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("CODEHARNESS_MODEL", "test-model")
    model = configured_model()
    assert model.model_name == "test-model"
    assert "synthetic-provider-canary" not in repr(model)
