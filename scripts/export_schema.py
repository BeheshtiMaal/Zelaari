"""Export the authoritative wire schema for TypeScript generation."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))

from agent.events import Protocol

target = root / "artifacts" / "protocol.schema.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(Protocol.model_json_schema(), indent=2), encoding="utf-8")
