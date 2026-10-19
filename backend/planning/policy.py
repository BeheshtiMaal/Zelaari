"""Pure plan review policy; scope approval never grants tool permission."""

import fnmatch
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from permissions.classifier import assess
from planning.types import FileScope, PlanningSettings, PlanRecord, PlanSubmission
from tools.jail import JailError, resolve, storage_path

MAX_SCOPE_FILES = 10000


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def load_settings(root: Path) -> tuple[PlanningSettings, dict[str, Any], str]:
    path = storage_path(root, "config.json")
    raw = path.read_bytes() if path.exists() else None
    if raw is not None and len(raw) > 1_000_000:
        raise ValueError("Workspace config is too large")
    document = json.loads(raw) if raw is not None else {}
    if not isinstance(document, dict):
        raise ValueError("Workspace config must be an object")
    settings = PlanningSettings.model_validate(document.get("planning", {}))
    return settings, document, digest(raw.hex() if raw is not None else None)


def merged_settings(root: Path, settings: PlanningSettings) -> str:
    _, document, _ = load_settings(root)
    return json.dumps({**document, "planning": settings.model_dump()}, ensure_ascii=False, indent=2)


def matches(path: str, pattern: str) -> bool:
    # Windows workspace paths are case-insensitive. **/ also includes root matches.
    target, glob = path.casefold(), pattern.casefold()
    return fnmatch.fnmatchcase(target, glob) or (
        glob.startswith("**/") and fnmatch.fnmatchcase(target, glob[3:])
    )


def file_scope(root: Path, submission: PlanSubmission) -> FileScope:
    patterns = {pattern for step in submission.steps for pattern in step.expected_files}
    concrete: set[str] = set()
    uncertain = False
    wildcards = {pattern for pattern in patterns if any(char in pattern for char in "*?[")}
    for pattern in patterns - wildcards:
        target = resolve(root, pattern)
        if target.path.is_dir():
            uncertain = True
        else:
            concrete.add(target.relative.casefold())
    matched: set[str] = set()
    visited = 0
    if wildcards:
        for directory, directories, files in os.walk(root, followlinks=False):
            if any(
                name.casefold() == ".git"
                or (Path(directory) / name).is_symlink()
                or (Path(directory) / name).is_junction()
                for name in directories
            ):
                uncertain = True
            directories[:] = [
                name
                for name in directories
                if name.casefold() not in {".harness", ".git"}
                and not (Path(directory) / name).is_symlink()
                and not (Path(directory) / name).is_junction()
            ]
            for name in files:
                visited += 1
                if visited > MAX_SCOPE_FILES:
                    uncertain = True
                    break
                relative = (Path(directory) / name).relative_to(root).as_posix()
                hits = {pattern for pattern in wildcards if matches(relative, pattern)}
                if hits:
                    try:
                        target = resolve(root, relative)
                    except JailError:
                        uncertain = True
                        continue
                    concrete.add(target.relative.casefold())
                    matched.update(hits)
            if visited > MAX_SCOPE_FILES:
                break
        uncertain = uncertain or matched != wildcards
    if len(concrete) > MAX_SCOPE_FILES:
        uncertain = True
    files = sorted(concrete)[:MAX_SCOPE_FILES]
    return FileScope(known_files=files, uncertain=uncertain, revision=digest([files, uncertain]))


def initial_reasons(
    root: Path,
    submission: PlanSubmission,
    scope: FileScope,
    settings: PlanningSettings,
    mode: str,
) -> list[str]:
    if mode == "auto":
        return []
    reasons: list[str] = []
    if len(submission.steps) >= settings.step_threshold:
        reasons.append("step_threshold")
    if len(scope.known_files) > settings.file_threshold:
        reasons.append("file_threshold")
    if scope.uncertain:
        reasons.append("uncertain_file_scope")
    if any(
        step.high_risk
        or (step.verify_command and assess(step.verify_command, root).level == "high")
        for step in submission.steps
    ):
        reasons.append("high_risk")
    return reasons


def deviation_reasons(previous: PlanRecord, proposed: PlanSubmission) -> list[str]:
    if not previous.settings.deviation_gate:
        return []
    old = {step.id: step for step in previous.submission.steps}
    new = {step.id: step for step in proposed.steps}
    reasons: list[str] = []
    if old.keys() - new.keys():
        reasons.append("dropped_step")
    if len(new.keys() - set(previous.baseline_ids)) > 2:
        reasons.append("added_steps")
    for identity in old.keys() & new.keys():
        before, after = old[identity], new[identity]
        if (
            set(before.expected_files) != set(after.expected_files)
            or before.high_risk != after.high_risk
            or before.verify_command != after.verify_command
        ):
            reasons.append("changed_scope_or_risk")
            break
    return reasons


def review_material(root: Path, submission: PlanSubmission) -> dict[str, Any]:
    settings, _, config_revision = load_settings(root)
    scope = file_scope(root, submission)
    return {
        "submission": submission.model_dump(mode="json"),
        "settings": settings.model_dump(mode="json"),
        "config_revision": config_revision,
        "file_scope": scope.model_dump(mode="json"),
    }
