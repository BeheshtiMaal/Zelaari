import type { ReactNode } from "react";

/** One settings section: the mock's heading row, then the section's own cards. */
export function SettingsFrame({ title, intro, action, children }: { title: string; intro: string; action?: ReactNode; children: ReactNode }) {
  return <section className="settings-content">
    <header className="settings-heading"><div><h2>{title}</h2><p className="muted">{intro}</p></div>{action}</header>
    {children}
  </section>;
}
