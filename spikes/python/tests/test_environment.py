import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path


def test_locked_environment() -> None:
    root = Path(__file__).resolve().parents[2]
    assert sys.version_info[:2] == (3, 12)
    lock = tomllib.loads((root / "python/uv.lock").read_text(encoding="utf8"))
    for package in lock["package"]:
        if package["name"] != "codeharness-spikes":
            assert importlib.metadata.version(package["name"]) == package["version"]
    manifest = json.loads((root / "ui/package.json").read_text(encoding="utf8"))
    npm_lock = json.loads((root / "ui/package-lock.json").read_text(encoding="utf8"))
    for name, version in (manifest["dependencies"] | manifest["devDependencies"]).items():
        assert npm_lock["packages"]["node_modules/" + name]["version"] == version
