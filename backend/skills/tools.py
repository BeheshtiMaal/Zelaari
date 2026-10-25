"""`load_skill`: the second half of progressive disclosure.

The tool result is the only place a skill body appears. It is bounded, redacted like any
other tool result, and refused when the person turned the skill off or the scan blocked it.
"""

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from skills.registry import Registry
from skills.scan import describe
from store.secrets import Redactor

MAX_BODY = 16_000


class LoadSkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=64, description="Skill folder name")


def build_load_skill(registry: Registry, redactor: Redactor | None = None) -> BaseTool:
    def load_skill(name: str) -> str:
        scrub = redactor or Redactor()
        record = registry.find(name)
        if record is None:
            known = ", ".join(item.name for item in registry.enabled()) or "none"
            return f"Unknown skill: {name}. Enabled skills: {known}"
        if record.problem:
            return f"Skill {name} is not usable: {record.problem}"
        if not record.enabled:
            return (
                f"Skill {name} is disabled for this workspace. "
                "The person can enable it in Customize > Skills."
            )
        detail = registry.detail(record)
        if detail.scan.status == "blocked":
            return (
                f"Skill {name} is blocked by the security scan "
                f"({', '.join(detail.scan.findings)}). It was not loaded."
            )
        scripts = ", ".join(detail.scan.scripts) or "none"
        header = (
            f"# {record.name} ({record.source})\n"
            f"{describe(detail.scan)}\n"
            f"scripts: {scripts}\n"
            f"references: {', '.join(detail.references) or 'none'}"
        )
        body = detail.body[:MAX_BODY]
        return scrub.text(f"{header}\n\n{body}".strip())

    return StructuredTool.from_function(
        func=load_skill,
        name="load_skill",
        description=(
            "Read a skill's full instructions by name. The prompt only carries names and "
            "descriptions; call this when a skill applies to the task. Returns the body, "
            "its scripts and its security-scan result."
        ),
        args_schema=LoadSkillInput,
    )
