export interface AppInfo {
  name: string;
  version: string;
  appData: string;
  logDirectory: string;
}

export interface DesktopBridge {
  readonly baseUrl: string;
  readonly token: string;
  pickWorkspace(): Promise<string | null>;
  revealWorkspace(path: string): Promise<boolean>;
  saveModel(value: import("./protocol").ModelInput & { api_key?: string }): Promise<{ok: boolean}>;
  vaultStatus(): Promise<boolean>;
  testModelDraft(value: import("./protocol").ModelInput & { api_key?: string }): Promise<import("./protocol").ProviderRecord | null>;
  appInfo(): Promise<AppInfo | null>;
  revealAppData(): Promise<boolean>;
  openLogFolder(): Promise<boolean>;
  clearKeys(): Promise<{ok: boolean; keys: number}>;
}
declare global { interface Window { harness?: DesktopBridge } }

export function connection(): DesktopBridge | undefined { return window.harness; }
