"""The ceiling a workspace-defined agent runs under.

A custom agent is a *prompt*, not a capability grant: it may ask for any of the read tools
and nothing else. The intersection is computed here so the factory cannot widen it by
accident, and an unknown name is dropped rather than passed through.
"""

from planning.readonly import SAFE_READ_TOOLS

MAX_TOOLS = 8


def allowed(names: list[str]) -> list[str]:
    """The requested read tools, sorted, deduplicated, and never outside the ceiling."""
    if not names:
        return sorted(SAFE_READ_TOOLS)
    wanted = {name.strip() for name in names if name.strip()} & SAFE_READ_TOOLS
    return sorted(wanted)[:MAX_TOOLS]


def rejected(names: list[str]) -> list[str]:
    """The names a person asked for that the ceiling does not include."""
    return sorted({name.strip() for name in names if name.strip()} - SAFE_READ_TOOLS)
