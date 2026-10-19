import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.events import RunRequest
from providers.base import ModelInput, infer_kind


def test_presets_and_inference() -> None:
    path = Path(__file__).parents[1] / "providers" / "presets.json"
    values = {item["name"]: item["url"] for item in json.loads(path.read_text())}
    assert values == {
        "OpenAI": "https://api.openai.com/v1", "Anthropic": "https://api.anthropic.com",
        "Jev": None, "AvalAI": "https://api.avalai.ir/v1", "Metis": None,
    }
    assert infer_kind(values["Anthropic"]) == "anthropic"
    assert infer_kind("https://api.anthropic.com.evil.invalid") == "openai-compatible"
    assert infer_kind("https://API.ANTHROPIC.COM/") == "anthropic"


def test_model_contract_and_arbitrary_run_id() -> None:
    assert RunRequest(task="read", workspace="project", model="user-123").mode == "ask"
    for url in ["file:///a", "https://user:secret@example.com", "https://x/?key=secret"]:
        with pytest.raises(ValidationError):
            ModelInput(id="a", name="a", model="b", base_url=url)
    with pytest.raises(ValidationError):
        ModelInput.model_validate(dict(id="a", name="a", model="b", base_url="https://x", price=1))
