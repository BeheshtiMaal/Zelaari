"use client";
import { genuiCopy } from "../i18n/genui";
import { currentLocale } from "../lib/locale";
import type { HarnessEvent } from "../lib/protocol";
import { Message } from "./message";

type RenderEvent = Extract<HarnessEvent, { type: "ui.render" }>;

/**
 * One rendering attempt. On success the program is drawn; on failure the note carries the
 * engine's one-line reason, so a broken program is never silently replaced by nothing.
 */
export function UiBlock({ event }: { event: RenderEvent }) {
  const t = genuiCopy(currentLocale());
  if (event.ok) return <div className="ui-block" data-testid="ui-block">
    <Message text={event.text} streaming={false} />
  </div>;
  return <p className="ui-fallback" data-testid="ui-fallback" role="status">
    <span>{t.renderFailed}</span>
    <code dir="ltr">{event.error ?? ""}</code>
  </p>;
}
