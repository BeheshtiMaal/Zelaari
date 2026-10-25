"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { toSchedule, type Schedule } from "./schedule";
import type { ScheduleInput, ScheduleList, ScheduleRecord } from "./protocol";

/** Local wall clock, because the engine's schedule times are local wall clock too. */
function localNow(): string {
  const at = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;
}

export function useSchedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [pending, setPending] = useState<Record<string, number>>({});
  const [now, setNow] = useState(localNow);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<"load" | "save" | "run" | null>(null);

  const load = useCallback(async () => {
    try {
      const payload = await api<ScheduleList>("/schedules");
      setSchedules((payload.schedules ?? []).map(toSchedule));
      setPending(payload.pending ?? {});
      // The engine's clock, not the renderer's: "next run" must not disagree with the ticker.
      setNow(payload.now);
      setError(null);
    } catch {
      setError("load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const submit = useCallback(
    async (call: () => Promise<unknown>, failure: "save" | "run") => {
      if (busy) return false;
      setBusy(true);
      setError(null);
      try {
        await call();
        await load();
        return true;
      } catch {
        setError(failure);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [busy, load],
  );

  return {
    schedules,
    pending,
    now,
    loading,
    busy,
    error,
    reload: load,
    create: (value: ScheduleInput) => submit(() => api<ScheduleRecord>("/schedules", "POST", value), "save"),
    update: (id: string, value: ScheduleInput) => submit(() => api(`/schedules/${id}`, "PUT", value), "save"),
    remove: (id: string) => submit(() => api(`/schedules/${id}`, "DELETE"), "save"),
    toggle: (id: string, enabled: boolean) => submit(() => api(`/schedules/${id}/enabled`, "POST", { enabled }), "save"),
    runNow: (id: string) => submit(() => api(`/schedules/${id}/run`, "POST"), "run"),
    skip: (id: string) => submit(() => api(`/schedules/${id}/skip`, "POST"), "save"),
  };
}
