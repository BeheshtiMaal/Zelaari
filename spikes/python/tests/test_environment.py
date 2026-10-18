import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path


def test_locked_environment() -> None:
    root = Path(__file__).resolve().parents[2]
    assert sys.version_info[:2] == (3, 12)
    lock = tomllib.loads((root / "python/uv.lock").read_text(encoding="utf8"))
    locked = {p["name"].replace("_", "-").lower(): p["version"] for p in lock["package"]}
    # uv locks alternate-platform dependencies too (e.g. WASM httpx2-jsfetch).
    # Validate every installed distribution without requiring foreign targets.
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"].replace("_", "-").lower()
        assert locked[name] == distribution.version
    manifest = json.loads((root / "ui/package.json").read_text(encoding="utf8"))
    npm_lock = json.loads((root / "ui/package-lock.json").read_text(encoding="utf8"))
    for name, version in (manifest["dependencies"] | manifest["devDependencies"]).items():
        assert npm_lock["packages"]["node_modules/" + name]["version"] == version
