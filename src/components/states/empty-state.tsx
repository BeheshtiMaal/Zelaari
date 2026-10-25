"use client";
import type { ReactNode } from "react";

export interface StateAction {
  label: string;
  onClick(): void;
  testId: string;
  /** The one action the state is asking for. A card has at most one. */
  primary?: boolean;
  disabled?: boolean;
}

export interface StateChip {
  label: string;
  value: string;
}

/**
 * The one empty state.
 *
 * The layout is the mock's: a 56px circle, a 16px title, 13.5px help that never runs
 * wider than 320px, and at most two actions so the choice stays a choice. A chip is not
 * an action: it fills the composer, and the person still decides to send.
 */
export function EmptyState({ icon, label, title, help, actions = [], chips = [], onChip, testId }: {
  icon: ReactNode;
  label?: string;
  title: string;
  help: string;
  actions?: StateAction[];
  chips?: StateChip[];
  onChip?(value: string): void;
  testId: string;
}) {
  return <section className="empty-state" data-testid={testId}>
    {label && <div className="empty-state-label">{label}</div>}
    <div className="empty-state-body">
      <span className="empty-icon" aria-hidden="true">{icon}</span>
      <strong>{title}</strong>
      <p>{help}</p>
      {actions.length > 0 && <div className="button-row">
        {actions.slice(0, 2).map(action => <button key={action.testId} type="button" data-testid={action.testId}
          className={action.primary ? "primary" : undefined} disabled={action.disabled}
          onClick={action.onClick}>{action.label}</button>)}
      </div>}
      {chips.length > 0 && onChip && <div className="empty-state-chips">
        {chips.map(chip => <button key={chip.value} type="button" data-testid={`chip-${chip.value}`}
          onClick={() => onChip(chip.value)}>{chip.label}</button>)}
      </div>}
    </div>
  </section>;
}
