"""The run's view of what is installed, enabled and safe to hand to the model."""

from dataclasses import dataclass, field
from pathlib import Path

from skills import loader
from skills.prompt import commands, skills_block
from skills.state import load_state
from skills.types import SkillCommand, SkillDetail, SkillRecord, SkillsState


@dataclass
class Registry:
    """Built once per run: discovery is a filesystem walk, not a model decision."""

    workspace: Path
    app_data: Path | None = None
    state: SkillsState = field(default_factory=SkillsState)
    records: list[SkillRecord] = field(default_factory=list)

    @classmethod
    def build(
        cls, workspace: Path, app_data: Path | None = None, state: SkillsState | None = None
    ) -> "Registry":
        switches = state if state is not None else load_state(workspace)
        return cls(
            workspace=workspace,
            app_data=app_data,
            state=switches,
            records=loader.discover(workspace, app_data, switches),
        )

    def enabled(self) -> list[SkillRecord]:
        return [record for record in self.records if record.enabled and not record.problem]

    def find(self, name: str) -> SkillRecord | None:
        return loader.find(self.records, name)

    def detail(self, record: SkillRecord) -> SkillDetail:
        return loader.detail(record, self.workspace, self.app_data)

    def block(self) -> str:
        return skills_block(self.records)

    def commands(self) -> list[SkillCommand]:
        return commands(self.records)

    def has_command(self, name: str) -> bool:
        return any(item.name == name for item in self.commands())
