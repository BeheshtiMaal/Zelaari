import { contextBridge, ipcRenderer } from "electron";
import type { EngineConnection } from "./sidecar";

const connection = ipcRenderer.sendSync("engine-connection") as EngineConnection;
contextBridge.exposeInMainWorld("harness", Object.freeze({
  baseUrl: connection.baseUrl, token: connection.token,
  pickWorkspace: (): Promise<string | null> => ipcRenderer.invoke("pick-workspace"),
}));
