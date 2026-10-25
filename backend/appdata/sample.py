"""The bundled sample project, materialised into app data on first use.

It is copied rather than opened in place: the app's own files must never be a workspace,
and a person who edits the sample should be editing their copy.
"""

import shutil
import sys
from pathlib import Path

NAME = "sample-project"
"""The folder name under app data, and the workspace name the person sees."""


def source() -> Path | None:
    """Where the sample ships, or `None` when this build has no copy of it.

    Two layouts are real: a source checkout (`<repo>/examples/sample-project`) and a
    packaged engine, where `build-engine.ps1` copies `examples/` next to the executable.
    """
    candidates = (
        Path(__file__).resolve().parents[2] / "examples" / NAME,
        Path(sys.executable).resolve().parent / "examples" / NAME,
    )
    return next((path for path in candidates if (path / "README.md").is_file()), None)


def materialise(bundle: Path, app_data: Path) -> Path:
    """Copy the sample into `app_data` once. An existing copy is never overwritten.

    The second click on "sample project" therefore lands on the same folder the person
    may already have edited, instead of silently undoing their work.
    """
    destination = app_data / NAME
    if not destination.exists():
        shutil.copytree(bundle, destination, dirs_exist_ok=True)
    return destination
