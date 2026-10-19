"use client";
import { create } from "zustand";
import { useEffect, useRef, useState } from "react";
import type { QuestionRecord } from "./protocol";
import type { QuestionSelection } from "./questions";
import { api } from "./api";
import { chooseOption, initialSelection, rankDrop, rankMove, validSelection } from "./questions";
import { useInbox } from "./inbox";

interface QuestionStore {
  records: Record<string, QuestionRecord[]>;
  failed: Record<string, boolean>;
  refresh(runId: string): Promise<void>;
}
export const useQuestionStore = create<QuestionStore>((set) => ({
  records: {}, failed: {},
  async refresh(runId) {
    try {
      const records = await api<QuestionRecord[]>(`/runs/${runId}/questions`);
      set(state => ({ records: { ...state.records, [runId]: records }, failed: { ...state.failed, [runId]: false } }));
    } catch { set(state => ({ failed: { ...state.failed, [runId]: true } })); }
  },
}));
const emptyRecords: QuestionRecord[] = [];
export function useQuestions(runId: string | null) {
  const records = useQuestionStore(state => runId ? state.records[runId] ?? emptyRecords : emptyRecords);
  useEffect(() => {
    if (!runId) return;
    void useQuestionStore.getState().refresh(runId);
    const timer = setInterval(() => void useQuestionStore.getState().refresh(runId), 900);
    return () => clearInterval(timer);
  }, [runId]);
  return records;
}
const drafts = new Map<string, Record<string, QuestionSelection>>();
const submissions = new Set<string>();
export function useQuestionEditor(record: QuestionRecord) {
  const key = `${record.request.run_id}/${record.request.call_id}`;
  const [answers, setAnswers] = useState<Record<string, QuestionSelection>>(() => drafts.get(key) ?? Object.fromEntries(record.request.questions.map(q => [q.id, initialSelection(q)])));
  const [index, setIndex] = useState(0), [error, setError] = useState(false), [busy, setBusy] = useState(false), [invalid, setInvalid] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const locked = useRef(false);
  const question = record.request.questions[index], selection = answers[question.id];
  const announceOrder = (ids: string[]) => ids.map(id => question.options.find(option => option.id === id)?.label ?? id).join(", ");
  function update(value: QuestionSelection) { const next = { ...answers, [question.id]: value }; drafts.set(key, next); setAnswers(next); setInvalid(false); }
  function choose(id: string) { update(chooseOption(question, selection, id)); }
  function other(value: string | null) { update({ ...selection, other: value, ...(question.type === "single" ? { option_ids: [], hint: null } : {}) }); }
  function move(id: string, direction: -1 | 1) { const next = rankMove(selection, id, direction); update(next); setAnnouncement(announceOrder(next.option_ids)); }
  async function send(declined = false) {
    if (locked.current || submissions.has(key) || record.status !== "pending") return;
    if (!declined && !record.request.questions.every(q => validSelection(q, answers[q.id]))) { setInvalid(true); return; }
    locked.current = true; submissions.add(key); setBusy(true); setError(false);
    try {
      await api(`/runs/${encodeURIComponent(record.request.run_id)}/interrupts/${encodeURIComponent(record.request.call_id)}`, "POST", {
        kind: "question", interrupt_id: record.interrupt_id, status: declined ? "declined" : "answered",
        answers: declined ? [] : record.request.questions.map(q => answers[q.id]),
      });
      drafts.delete(key);
      await useQuestionStore.getState().refresh(record.request.run_id);
      await useInbox.getState().refresh();
    } catch { setError(true); }
    finally { locked.current = false; submissions.delete(key); setBusy(false); }
  }
  function advance() {
    if (!validSelection(question, selection)) { setInvalid(true); return; }
    if (index < record.request.questions.length - 1) { setIndex(index + 1); setInvalid(false); }
    else void send();
  }
  return { question, selection, index, busy, error, invalid, announcement, choose, other, move, advance, send,
    drop: (id: string, target: string) => { const next = rankDrop(selection, id, target); update(next); setAnnouncement(announceOrder(next.option_ids)); },
    back: () => { setIndex(Math.max(0, index - 1)); setInvalid(false); },
    hint: (value: string) => update({ ...selection, hint: value || null }),
  };
}
