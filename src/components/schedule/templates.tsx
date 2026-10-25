"use client";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import { GitBranchIcon } from "@phosphor-icons/react/dist/csr/GitBranch";
import { FolderSimpleIcon } from "@phosphor-icons/react/dist/csr/FolderSimple";
import { ChartBarIcon } from "@phosphor-icons/react/dist/csr/ChartBar";
import { ListChecksIcon } from "@phosphor-icons/react/dist/csr/ListChecks";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/csr/CalendarDots";
import type { ReactNode } from "react";
import type { ScheduleCopy } from "../../i18n/schedule";

/** The mock gives each card its own icon; the id is what ties a card to its icon. */
const ICONS: Record<string, ReactNode> = {
  "nightly-tests": <ShieldCheckIcon size={22} />,
  "git-review": <GitBranchIcon size={22} />,
  dependencies: <FolderSimpleIcon size={22} />,
  coverage: <ChartBarIcon size={22} />,
  todos: <ListChecksIcon size={22} />,
  "weekly-summary": <CalendarDotsIcon size={22} />,
};

/**
 * The six templates. A click fills the dialog; it never creates anything, because a card
 * that starts running tasks on one click is a card that can schedule work by accident.
 */
export function Templates({ copy, onPick, disabled }: {
  copy: ScheduleCopy; onPick(id: string): void; disabled?: boolean;
}) {
  return <div className="schedule-templates">
    {copy.templates.map(template => <button key={template.id} type="button" className="schedule-template"
      data-testid={`schedule-template-${template.id}`} disabled={disabled} onClick={() => onPick(template.id)}>
      <span className="schedule-template-icon" aria-hidden="true">{ICONS[template.id] ?? <CalendarDotsIcon size={22} />}</span>
      <span className="schedule-template-text"><strong>{template.name}</strong><small>{template.prompt}</small></span>
    </button>)}
  </div>;
}
