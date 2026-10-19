export interface DesktopBridge {
  readonly baseUrl: string;
  readonly token: string;
  pickWorkspace(): Promise<string | null>;
  saveModel(value: import("./protocol").ModelInput & { api_key?: string }): Promise<{ok: boolean}>;
  vaultStatus(): Promise<boolean>;
}
declare global { interface Window { harness?: DesktopBridge } }

export function connection(): DesktopBridge | undefined { return window.harness; }
