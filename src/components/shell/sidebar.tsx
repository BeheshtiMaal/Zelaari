import { GearIcon } from "@phosphor-icons/react/dist/csr/Gear";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { PlusCircleIcon } from "@phosphor-icons/react/dist/csr/PlusCircle";
import { TrayIcon } from "@phosphor-icons/react/dist/csr/Tray";
import { SparkleIcon } from "@phosphor-icons/react/dist/csr/Sparkle";
import { AlarmIcon } from "@phosphor-icons/react/dist/csr/Alarm";
import type { Dictionary } from "../../i18n";

export function Sidebar({ t, reset, disabled }: { t: Dictionary; reset(): void; disabled: boolean }) {
  return <aside className="sidebar" aria-label="CodeHarness">
    <div className="brand"><span className="brand-mark" /><span dir="ltr">CodeHarness</span></div>
    <nav>
      <button className="nav-item active" onClick={reset} disabled={disabled}><PlusCircleIcon size={18} /><span>{t.newTask}</span></button>
      <button className="nav-item" disabled title={t.soon}><TrayIcon size={18} /><span>{t.approvals}</span></button>
      <button className="nav-item" disabled title={t.soon}><SparkleIcon size={18} /><span>{t.customize}</span></button>
      <button className="nav-item" disabled title={t.soon}><AlarmIcon size={18} /><span>{t.schedule}</span></button>
    </nav>
    <div className="workspace-label">{t.workspaces}</div>
    <button className="nav-item" disabled title={t.soon}><FolderIcon size={18} /><span>{t.workspaces}</span></button>
    <button className="nav-item settings" disabled title={t.soon}><GearIcon size={18} /><span>{t.settings}</span></button>
  </aside>;
}
