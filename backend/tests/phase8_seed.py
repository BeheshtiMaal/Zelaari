"""Seed the Phase 8 walkthrough: one workspace, one project skill, one fake MCP server.

The skill is a real folder in the workspace's own skills root, so the walkthrough sees it
through the product's loader, scan and prompt block rather than through a fixture the UI
knows about. The server is a plain Python file in the project, which is what an MCP server
in a repository looks like.

The marker in the body is the point: progressive disclosure is only proven if the body text
can be searched for and never found in the prompt.
"""

import json
import shutil
import sys
from pathlib import Path

from skills.registry import Registry

MARKER = "BODY-MARKER-8f3a"
DESCRIPTION = "Draft release notes from merged changes, one section per user-visible change."

SKILL = f"""---
name: release-notes
description: {DESCRIPTION}
command: /notes
category: docs
---

# Release notes

{MARKER}

Write for the person who upgrades, not for the person who wrote the change. One section per
user-visible change, in the order a reader meets it: what broke, what is new, what moved.

## Shape

- A heading that names the change, not the ticket.
- One sentence on what the person can now do that they could not before.
- A migration line only when something they wrote will stop working.

## Checks

- Every entry names something a user can see or do.
- No internal ticket numbers, branch names or reviewer names.
- The shortest entry that is still true wins.
"""

README = """# Release notes fixture

This project ships a skill that drafts release notes and a small MCP server.
"""

CONFIG = {
    "context": {"compaction_percent": 60, "keep_messages": 8, "offload": True, "show_ring": True},
    "verify": {
        "gate": True,
        "command": None,
        "max_steps": 40,
        "max_minutes": 30,
        "fix_attempts": 3,
    },
    "terminal": {"shell": "auto", "timeout_seconds": 120, "max_output_lines": 200},
}


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def project(root: Path) -> None:
    write(root, "README.md", README)
    write(root, ".harness/config.json", json.dumps(CONFIG, ensure_ascii=False, indent=2))
    write(root, ".harness/skills/release-notes/SKILL.md", SKILL)
    write(
        root,
        ".harness/skills/release-notes/references/style.md",
        "# Style\n\nShort sentences. Present tense. The reader is the subject.\n",
    )
    # The same server the engine's own connector tests speak to.
    shutil.copyfile(
        Path(__file__).with_name("mcp_worker.py"), write(root, "tools/mcp_fake.py", "")
    )


def main() -> None:
    workspace = Path(sys.argv[1])
    project(workspace)
    registry = Registry.build(workspace, None)
    record = registry.find("release-notes")
    assert record is not None, "the project skill was not discovered"
    assert record.source == "workspace", record.source
    assert record.problem is None, record.problem
    assert record.scan.status == "clean", record.scan
    assert record.command == "/notes", record.command
    assert record.enabled, "a project skill is on unless the person turns it off"
    assert record.tokens > 0, "the description must cost something in context"
    assert registry.find("web-search") is not None, "the bundled skills are missing"
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "skill": str(workspace / ".harness" / "skills" / "release-notes" / "SKILL.md"),
                "description": DESCRIPTION,
                "marker": MARKER,
                "server": str(workspace / "tools" / "mcp_fake.py"),
                "python": sys.executable,
                "skills": len(registry.records),
            }
        )
    )


if __name__ == "__main__":
    main()
