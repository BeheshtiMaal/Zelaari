import { contextBridge, ipcRenderer } from "electron";
import type { EngineConnection } from "./sidecar";

// Captured once: `contextBridge` copies values, so a restart cannot update these. The
// renderer adopts the new pair from `restartEngine()` and answers through `connection()`
// in `src/lib/desktop.ts`; nothing in the app reads these two after startup.
const connection = ipcRenderer.sendSync("engine-connection") as EngineConnection;
contextBridge.exposeInMainWorld("harness", Object.freeze({
  baseUrl: connection.baseUrl, token: connection.token,
  pickWorkspace: (): Promise<string | null> => ipcRenderer.invoke("pick-workspace"),
  revealWorkspace: (path: string): Promise<boolean> => ipcRenderer.invoke("reveal-workspace", path),
  saveModel: (value: unknown): Promise<{ok: boolean}> => ipcRenderer.invoke("save-model", value),
  vaultStatus: (): Promise<boolean> => ipcRenderer.invoke("vault-status"),
  testModelDraft: (value: unknown): Promise<unknown> => ipcRenderer.invoke("test-model-draft", value),
  appInfo: (): Promise<{name: string; version: string; appData: string; logDirectory: string} | null> => ipcRenderer.invoke("app-info"),
  revealAppData: (): Promise<boolean> => ipcRenderer.invoke("reveal-app-data"),
  openLogFolder: (): Promise<boolean> => ipcRenderer.invoke("open-log-folder"),
  clearKeys: (): Promise<{ok: boolean; keys: number}> => ipcRenderer.invoke("clear-keys"),
  // A restart is a new port and a new token, so the caller has to replace what it holds.
  restartEngine: (): Promise<EngineConnection | null> => ipcRenderer.invoke("restart-engine"),
  onEngineStatus: (callback: (alive: boolean) => void): (() => void) => {
    const listener = (_event: unknown, value: { alive?: boolean }): void => callback(value?.alive !== false);
    ipcRenderer.on("engine-status", listener);
    return () => { ipcRenderer.removeListener("engine-status", listener); };
  },
}));
