"use client";
import { useState } from "react";
import { AlarmIcon } from "@phosphor-icons/react/dist/csr/Alarm";
import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import type { Session } from "../../lib/use-session";
import { scheduleCopy } from "../../i18n/schedule";
import { statesCopy } from "../../i18n/states";
import { localeDigits } from "../../lib/localised-number";
import {
  draftFrom,
  draftFromTemplate,
  emptyDraft,
  type Schedule,
  type ScheduleDraft,
} from "../../lib/schedule";
import type { ScheduleInput } from "../../lib/protocol";
import { useSchedules } from "../../lib/use-schedules";
import { EmptyState } from "../states/empty-state";
import { ScheduleRow } from "./schedule-row";
import { Templates } from "./templates";
import { ScheduleDialog } from "./schedule-dialog";
import { DeleteSchedule } from "./delete-schedule";

type Editing = { draft: ScheduleDraft; id: string | null };

/**
 * The Schedule screen.
 *
 * The subtitle is the promise the whole feature has to keep: these run only while the app is
 * open, and anything that needs a person waits for one. The empty state offers the one action
 * that fixes it, and the templates fill the dialog rather than creating work by themselves.
 */
export function ScheduleScreen({ session }: { session: Session }) {
  const copy = scheduleCopy(session.locale), states = statesCopy(session.locale);
  const store = useSchedules();
  const [editing, setEditing] = useState<Editing | null>(null);
  const [removing, setRemoving] = useState<Schedule | null>(null);

  const workspaces = (session.spaces.recent ?? []).map(item => ({ path: item.path, name: item.name }));
  const base = emptyDraft(session.workspace || workspaces[0]?.path || "", session.model || "demo");
  const active = store.schedules.filter(item => item.enabled);
  const paused = store.schedules.filter(item => !item.enabled);
  const canCreate = base.workspace !== "";

  const openNew = () => { if (canCreate) setEditing({ draft: base, id: null }); };
  const openTemplate = (id: string) => {
    const template = copy.templates.find(item => item.id === id);
    if (!template || !canCreate) return;
    setEditing({ draft: draftFromTemplate(template, base), id: null });
  };
  const openEdit = (schedule: Schedule) => setEditing({ draft: draftFrom(schedule), id: schedule.id });

  const save = async (value: ScheduleInput) => {
    const ok = editing?.id ? await store.update(editing.id, value) : await store.create(value);
    if (ok) setEditing(null);
    return ok;
  };

  const row = (schedule: Schedule) => <ScheduleRow key={schedule.id} schedule={schedule} locale={session.locale}
    copy={copy} now={store.now} busy={store.busy} pending={store.pending[schedule.id] ?? 0}
    onToggle={enabled => void store.toggle(schedule.id, enabled)}
    onEdit={() => openEdit(schedule)}
    onRunNow={() => void store.runNow(schedule.id)}
    onSkip={() => void store.skip(schedule.id)}
    onDelete={() => setRemoving(schedule)} />;

  return <div className="schedule-screen" data-testid="schedule-screen">
    <header className="customize-heading">
      <div><h1>{copy.title}</h1><p className="muted">{copy.subtitle}</p></div>
      <button type="button" className="light-button new-schedule" onClick={openNew} disabled={!canCreate || store.busy}
        title={canCreate ? undefined : copy.noWorkspace} data-testid="schedule-new">
        <PlusIcon size={16} />{copy.create}
      </button>
    </header>

    {store.error === "load" && <p className="error" role="alert" data-testid="schedule-load-error">{copy.loadError}</p>}
    {store.loading && <p className="muted">{copy.loading}</p>}

    {!store.loading && store.schedules.length === 0 && <EmptyState testId="state-no-schedules"
      icon={<AlarmIcon size={26} />} label={states.noSchedules.label} title={states.noSchedules.title}
      help={states.noSchedules.help}
      actions={[{ label: states.noSchedules.primary, testId: "state-add-schedule", primary: true, disabled: !canCreate, onClick: openNew }]} />}

    {active.length > 0 && <>
      <div className="schedule-group">{copy.active} ({localeDigits(active.length, session.locale)})</div>
      {active.map(row)}
    </>}
    {paused.length > 0 && <>
      <div className="schedule-group">{copy.paused} ({localeDigits(paused.length, session.locale)})</div>
      {paused.map(row)}
    </>}

    <div className="schedule-templates-heading">{copy.templatesTitle}</div>
    <Templates copy={copy} onPick={openTemplate} disabled={!canCreate || store.busy} />

    {store.error === "save" && <p className="error" role="alert">{copy.saveError}</p>}
    {store.error === "run" && <p className="error" role="alert">{copy.runError}</p>}

    {editing && <ScheduleDialog copy={copy} locale={session.locale} draft={editing.draft}
      editing={editing.id !== null} workspaces={workspaces} busy={store.busy}
      error={store.error === "save" ? copy.saveError : null}
      onSave={save} close={() => setEditing(null)} />}

    {removing && <DeleteSchedule schedule={removing} copy={copy} busy={store.busy}
      onConfirm={() => void store.remove(removing.id).then(ok => { if (ok) setRemoving(null); })}
      close={() => setRemoving(null)} />}
  </div>;
}
