from pathlib import Path

import pytest

from providers.config import load_provider_env


def test_external_config_has_a_fixed_location_and_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    for name in ("CODEHARNESS_MODEL", "CODEHARNESS_API_KEY", "CODEHARNESS_BASE_URL"):
        monkeypatch.setenv(name, "")
    path = tmp_path / "CodeHarness" / "phase1-provider.env"
    path.parent.mkdir()
    path.write_text(
        '\ufeffCODEHARNESS_MODEL="fixture-model"\nCODEHARNESS_API_KEY=fixture-key\n'
        "CODEHARNESS_BASE_URL=https://example.invalid/v1\nLANGSMITH_TRACING=true\n",
        encoding="utf-8",
    )
    load_provider_env()
    import os

    assert os.environ["CODEHARNESS_MODEL"] == "fixture-model"
    assert os.environ["CODEHARNESS_API_KEY"] == "fixture-key"
    assert os.environ["LANGSMITH_TRACING"] == "false"
