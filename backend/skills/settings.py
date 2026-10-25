"""Where the search provider is configured: the `search` section of `.harness/config.json`.

It shares the file and the protected-configuration approval with the Phase 7 settings, but
not their model: a save here rewrites one section and leaves the rest byte-identical.
"""

import json
from pathlib import Path

from skills.search import SearchSettings
from verify.settings import read_document


def load_search(root: Path) -> SearchSettings:
    try:
        document = read_document(root)
    except (OSError, ValueError):
        return SearchSettings()
    try:
        return SearchSettings.model_validate(document.get("search") or {})
    except ValueError:
        return SearchSettings()


def merged_search(root: Path, value: SearchSettings) -> str:
    """Rewrite only `search`; every other key stays exactly as it was."""
    document = read_document(root)
    document["search"] = json.loads(value.model_dump_json())
    return json.dumps(document, ensure_ascii=False, indent=2)
