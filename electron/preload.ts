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
}));
