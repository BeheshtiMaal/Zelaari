export interface DesktopBridge {
  readonly baseUrl: string;
  readonly token: string;
  pickWorkspace(): Promise<string | null>;
}
declare global { interface Window { harness?: DesktopBridge } }

export function connection(): DesktopBridge | undefined { return window.harness; }
