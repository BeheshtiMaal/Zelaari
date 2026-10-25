"use client";
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { genuiCopy } from "../../i18n/genui";
import { currentLocale } from "../../lib/locale";

/**
 * Display-only tabs. Arrow keys follow the reading direction, Home and End jump to the ends,
 * and only the selected tab is in the tab order — the contract R14 documents.
 */
export function TabsView({ labels, panels }: { labels: string[]; panels: ReactNode[] }) {
  const t = genuiCopy(currentLocale());
  const base = useId();
  const [chosen, setChosen] = useState(0);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  if (labels.length === 0) return null;
  const active = Math.max(0, Math.min(chosen, labels.length - 1));
  const select = (index: number) => { setChosen(index); buttons.current[index]?.focus(); };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const rtl = typeof document !== "undefined" && document.documentElement.dir === "rtl";
    const step = (delta: number) => { event.preventDefault(); select((active + delta + labels.length) % labels.length); };
    if (event.key === "ArrowRight") return step(rtl ? -1 : 1);
    if (event.key === "ArrowLeft") return step(rtl ? 1 : -1);
    if (event.key === "Home") return step(-active);
    if (event.key === "End") return step(labels.length - 1 - active);
  };
  return <section className="genui-tabs" data-testid="genui-tabs">
    <div className="genui-tablist" role="tablist" aria-label={t.tabList}>
      {labels.map((label, index) => <button
        key={index}
        type="button"
        role="tab"
        id={`${base}-tab-${index}`}
        ref={node => { buttons.current[index] = node; }}
        aria-selected={index === active}
        aria-controls={`${base}-panel-${index}`}
        tabIndex={index === active ? 0 : -1}
        className="genui-tab"
        onClick={() => setChosen(index)}
        onKeyDown={onKeyDown}
      >{label}</button>)}
    </div>
    {labels.map((_, index) => <div
      key={index}
      role="tabpanel"
      id={`${base}-panel-${index}`}
      aria-labelledby={`${base}-tab-${index}`}
      hidden={index !== active}
      className="genui-tabpanel"
    >{panels[index] ?? null}</div>)}
  </section>;
}
