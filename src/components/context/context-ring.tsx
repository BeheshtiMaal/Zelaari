import * as Popover from "@radix-ui/react-popover";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { Locale } from "../../i18n";
import { contextCopy } from "../../i18n/context";
import { arcDash, ringLabel, usedPercent } from "../../lib/context-format";
import type { ContextUpdated } from "../../lib/protocol";
import { ContextBreakdown } from "./context-breakdown";

const RADIUS = 14;

export function ContextRing({ event, locale, threshold, summary, onNewChat, busy }: {
  event: ContextUpdated;
  locale: Locale;
  threshold: number;
  summary: boolean;
  onNewChat?(): void;
  busy: boolean;
}) {
  const t = contextCopy(locale);
  const window = event.context_window ?? null;
  const label = ringLabel(event.input_tokens, window, locale, {
    used: event.estimated, window: event.context_window_estimated ?? false,
  });
  const arc = arcDash(usedPercent(event.input_tokens, window), RADIUS);
  const text = `${label} ${t.ring}`;
  return <Tooltip.Provider delayDuration={150}>
    <Popover.Root>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <Popover.Trigger asChild>
            <button type="button" className="context-ring" data-testid="context-ring" aria-label={text}>
              <svg viewBox="0 0 36 36" width="22" height="22" aria-hidden="true">
                <circle className="ring-track" cx="18" cy="18" r={RADIUS} fill="none" strokeWidth="4" />
                <circle className="ring-arc" cx="18" cy="18" r={RADIUS} fill="none" strokeWidth="4" strokeLinecap="round"
                  strokeDasharray={arc.dasharray} strokeDashoffset={arc.dashoffset} transform="rotate(-90 18 18)" />
              </svg>
            </button>
          </Popover.Trigger>
        </Tooltip.Trigger>
        <Tooltip.Portal><Tooltip.Content className="tooltip" side="top" sideOffset={10}>{text}</Tooltip.Content></Tooltip.Portal>
      </Tooltip.Root>
      <Popover.Portal>
        <Popover.Content className="context-popover" side="top" align="end" sideOffset={10} aria-label={t.title}>
          <ContextBreakdown event={event} locale={locale} threshold={threshold} summary={summary} busy={busy} onNewChat={onNewChat} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  </Tooltip.Provider>;
}
