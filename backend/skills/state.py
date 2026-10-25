"""Per-workspace switches in `.harness/skills.json`.

Only the person's overrides live here, never a copy of a skill: an installed skill is a
folder, and this file answers "is it on for this workspace?".
"""

import json
from pathlib import Path

from skills.types import SkillsState
from tools.atomic import atomic_write
from tools.jail import storage_path

MAX_STATE_BYTES = 64_000
MAX_OVERRIDES = 500


def load_state(root: Path) -> SkillsState:
    """A missing or damaged file means "no overrides", never a failed run."""
    path = storage_path(root, "skills.json")
    try:
        if not path.is_file():
            return SkillsState()
        raw = path.read_bytes()
        if len(raw) > MAX_STATE_BYTES:
            return SkillsState()
        document = json.loads(raw)
    except (OSError, ValueError):
        return SkillsState()
    if not isinstance(document, dict):
        return SkillsState()
    overrides: dict[str, bool] = {}
    values = document.get("overrides")
    if isinstance(values, dict):
        for name, enabled in list(values.items())[:MAX_OVERRIDES]:
            if isinstance(name, str) and isinstance(enabled, bool):
                overrides[name] = enabled
    url = document.get("catalog_url")
    return SkillsState(
        overrides=overrides, catalog_url=url if isinstance(url, str) and url else None
    )


def save_state(root: Path, state: SkillsState) -> None:
    atomic_write(storage_path(root, "skills.json"), state.model_dump_json(indent=2))


def set_enabled(root: Path, name: str, enabled: bool) -> SkillsState:
    state = load_state(root)
    state.overrides[name] = enabled
    save_state(root, state)
    return state


def set_catalog(root: Path, url: str | None) -> SkillsState:
    state = load_state(root)
    state.catalog_url = url
    save_state(root, state)
    return state
