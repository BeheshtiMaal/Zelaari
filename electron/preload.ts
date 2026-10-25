import { contextBridge, ipcRenderer } from "electron";
import type { EngineConnection } from "./sidecar";

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
}));
