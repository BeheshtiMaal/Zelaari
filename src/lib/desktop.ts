export interface AppInfo {
  name: string;
  version: string;
  appData: string;
  logDirectory: string;
}

export interface EngineConnection {
  baseUrl: string;
  token: string;
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
  restartEngine(): Promise<EngineConnection | null>;
  onEngineStatus(callback: (alive: boolean) => void): () => void;
}
declare global { interface Window { harness?: DesktopBridge } }

/**
 * The connection a restarted engine handed back.
 *
 * The preload learns the new pair from the status event, but that event and the
 * `restart-engine` reply are separate messages: keeping the returned pair here means the
 * first request after a restart cannot race the broadcast. Everything else is the bridge.
 */
let live: EngineConnection | null = null;

export function connection(): DesktopBridge | undefined {
  const bridge = window.harness;
  if (!bridge) return undefined;
  return live ? { ...bridge, baseUrl: live.baseUrl, token: live.token } : bridge;
}

/** Adopt the connection a restart returned; until then the preload's pair is the truth. */
export function reconnect(value: EngineConnection): void {
  live = value;
}

/** The preload's original pair, for a test that needs to forget a restart. */
export function forgetConnection(): void {
  live = null;
}
