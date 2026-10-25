"use client";
import { useState } from "react";
import { settingsCopy } from "../../i18n/settings";
import { FONTS, LOCALES, THEMES, currentAppearance, segment } from "../../lib/appearance";
import type { Appearance } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { Row, Segment, Switch } from "./verify-rows";

export function AppearanceSection({ session }: { session: Session }) {
  const t = settingsCopy(session.locale), appearance = currentAppearance(session.settings);
  const [failed, setFailed] = useState(false);
  const change = (patch: Appearance) => { void session.changeAppearance(patch).then(ok => setFailed(!ok)); };
  return <>
    <section className="model-card" data-testid="appearance-display">
      <h3>{t.display}</h3>
      <Row title={t.language} help={t.languageDefault}>
        <Segment label={t.language} testId="appearance-locale" options={segment(LOCALES, [t.persian, t.english], session.locale)}
          onSelect={value => void session.setLocale(value)} />
      </Row>
      <Row title={t.theme} help={t.themeDefault}>
        <Segment label={t.theme} testId="appearance-theme" options={segment(THEMES, t.themes, appearance.theme)}
          onSelect={value => change({ theme: value })} />
      </Row>
      <Row title={t.font} help={t.fontHelp}>
        <Segment label={t.font} testId="appearance-font" options={segment(FONTS, t.fonts, appearance.font)}
          onSelect={value => change({ font: value })} />
      </Row>
    </section>
    <section className="model-card" data-testid="appearance-activity">
      <h3>{t.activity}</h3>
      <Row title={t.showThinking} help={t.showThinkingHelp}>
        <Switch checked={appearance.show_thinking} label={t.showThinking} testId="appearance-thinking"
          onChange={value => change({ show_thinking: value })} />
      </Row>
      <Row title={t.keepThinkingOpen} help={t.keepThinkingOpenHelp}>
        <Switch checked={appearance.keep_thinking_open} label={t.keepThinkingOpen} testId="appearance-keep-open"
          onChange={value => change({ keep_thinking_open: value })} />
      </Row>
      <Row title={t.showTerminal} help={t.showTerminalHelp}>
        <Switch checked={appearance.show_terminal} label={t.showTerminal} testId="appearance-terminal"
          onChange={value => change({ show_terminal: value })} />
      </Row>
    </section>
    {failed && <p className="error" role="alert" data-testid="appearance-error">{t.saveError}</p>}
  </>;
}
