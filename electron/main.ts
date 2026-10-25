import { app, BrowserWindow, dialog, ipcMain, net, protocol, safeStorage, shell } from "electron";
import { existsSync, statSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";
import { createLog } from "./log";
import { startSidecar, type Sidecar } from "./sidecar";
import { Vault, modelSubmission, trustedFrame } from "./vault";
import { validateWorkspace } from "./workspace";

app.disableHardwareAcceleration();
protocol.registerSchemesAsPrivileged([{ scheme: "app", privileges: {
  standard: true, secure: true, supportFetchAPI: true,
} }]);
if (process.env.CODEHARNESS_TEST_USER_DATA) app.setPath("userData", process.env.CODEHARNESS_TEST_USER_DATA);
const root = app.isPackaged ? process.resourcesPath : resolve(__dirname, "..");
let sidecar: Sidecar | undefined;

app.whenReady().then(async () => {
  const appData = app.getPath("userData");
  const logDirectory = join(appData, "logs");
  const log = createLog(logDirectory);
  const vault = new Vault(resolve(appData, "vault.json"), safeStorage);
  let vaultError = false;
  let initialized: Promise<import("./sidecar").EngineConnection> | undefined;
  // The renderer shows the crash card from this, so a dead engine is a state the app can
  // recover from rather than a window that disappears.
  const announce = (alive: boolean) => {
    for (const window of BrowserWindow.getAllWindows()) {
      if (!window.isDestroyed()) window.webContents.send("engine-status", { alive });
    }
  };
  const connect = () => initialized ??= (async () => {
    sidecar ??= startSidecar(root, app.isPackaged, () => {
      log("engine exited unexpectedly");
      announce(false);
    }, appData, log);
    const connection = await sidecar.ready;
    for (let attempt = 0; attempt < 120; attempt++) {
      try { if ((await fetch(connection.baseUrl + "/health", { headers: { Authorization: `Bearer ${connection.token}` } })).ok) break; }
      catch { /* Socket is announced just before the HTTP server starts. */ }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    try {
      for (const [id, key] of Object.entries(await vault.all())) {
        const response = await fetch(connection.baseUrl + "/internal/credentials", {
          method: "POST", headers: { Authorization: `Bearer ${connection.token}`, "Content-Type": "application/json" }, body: JSON.stringify({ id, key }),
        });
        if (!response.ok) throw new Error();
      }
    } catch { vaultError = true; }
    return connection;
  })();
  // Keep the native window responsive during cold Python imports.
  ipcMain.on("engine-connection", (event) => {
    if (!trustedFrame(event.senderFrame?.url)) {
      event.returnValue = { baseUrl: "", token: "" };
      return;
    }
    void connect().then(connection => { event.returnValue = connection; }, () => {
      event.returnValue = { baseUrl: "", token: "" };
    });
  });
  ipcMain.handle("vault-status", event => trustedFrame(event.senderFrame?.url) && !vaultError);
  ipcMain.handle("test-model-draft", async (event, input: unknown) => {
    if (!trustedFrame(event.senderFrame?.url)) return null;
    try {
      const { api_key, ...metadata } = modelSubmission.parse(input);
      const key = api_key ?? (await vault.all())[metadata.id];
      if (!key) return null;
      const connection = await connect();
      const response = await fetch(connection.baseUrl + "/internal/probe", {
        method: "POST", headers: { Authorization: `Bearer ${connection.token}`, "Content-Type": "application/json" }, body: JSON.stringify({ ...metadata, key }),
      });
      return response.ok ? await response.json() : null;
    } catch { return null; }
  });
  let saveQueue: Promise<unknown> = Promise.resolve();
  ipcMain.handle("save-model", (event, input: unknown) => {
    if (!trustedFrame(event.senderFrame?.url)) return { ok: false };
    const work = saveQueue.then(async () => {
      try {
        const { api_key, ...metadata } = modelSubmission.parse(input);
        const connection = await connect();
        const headers = { Authorization: `Bearer ${connection.token}`, "Content-Type": "application/json" };
        if (api_key) {
          await vault.put(metadata.id, api_key);
          const result = await fetch(connection.baseUrl + "/internal/credentials", { method: "POST", headers, body: JSON.stringify({ id: metadata.id, key: api_key }) });
          if (!result.ok) throw new Error();
        }
        const result = await fetch(connection.baseUrl + "/models", { method: "POST", headers, body: JSON.stringify(metadata) });
        if (!result.ok) throw new Error();
        vaultError = false;
        return { ok: true };
      } catch { return { ok: false }; }
    });
    saveQueue = work.catch(() => undefined);
    return work;
  });
  ipcMain.handle("pick-workspace", async (event) => {
    if (!trustedFrame(event.senderFrame?.url)) return null;
    const result = await dialog.showOpenDialog({ properties: ["openDirectory"] });
    if (result.canceled || !result.filePaths[0]) return null;
    try { return await validateWorkspace(result.filePaths[0]); }
    catch { throw new Error("Choose an accessible project folder, not a root or home"); }
  });
  // Opening Explorer is the only OS action the renderer can ask for, and only for a
  // folder that passes the same validation as the picker.
  ipcMain.handle("reveal-workspace", async (event, value: unknown) => {
    if (!trustedFrame(event.senderFrame?.url)) return false;
    try { const path = await validateWorkspace(String(value)); return (await shell.openPath(path)) === ""; }
    catch { return false; }
  });
  // The two folders the app owns. Neither takes a path from the renderer: the app-data root
  // and its log directory are the only places these can open.
  ipcMain.handle("app-info", event => trustedFrame(event.senderFrame?.url)
    ? { name: "CodeHarness", version: app.getVersion(), appData, logDirectory }
    : null);
  ipcMain.handle("reveal-app-data", async event => {
    if (!trustedFrame(event.senderFrame?.url)) return false;
    try { return (await shell.openPath(appData)) === ""; } catch { return false; }
  });
  ipcMain.handle("open-log-folder", async event => {
    if (!trustedFrame(event.senderFrame?.url)) return false;
    try {
      log("log folder opened");
      return (await shell.openPath(logDirectory)) === "";
    } catch { return false; }
  });
  ipcMain.handle("clear-keys", async event => {
    if (!trustedFrame(event.senderFrame?.url)) return { ok: false, keys: 0 };
    try {
      const connection = await connect();
      const response = await fetch(connection.baseUrl + "/internal/credentials", {
        method: "DELETE", headers: { Authorization: `Bearer ${connection.token}` },
      });
      if (!response.ok) return { ok: false, keys: 0 };
      const body = await response.json() as { keys?: number };
      await vault.clear();
      vaultError = false;
      log(`keys cleared count=${body.keys ?? 0}`);
      return { ok: true, keys: body.keys ?? 0 };
    } catch { return { ok: false, keys: 0 }; }
  });
  // A restart is a new process on a new port with a new token, so the renderer is handed
  // the new connection and re-runs its bootstrap with it. The old sidecar is closed first,
  // which is also what stops its exit from being reported as a crash.
  ipcMain.handle("restart-engine", async event => {
    if (!trustedFrame(event.senderFrame?.url)) return null;
    try {
      log("engine restart requested");
      sidecar?.close();
      sidecar = undefined;
      initialized = undefined;
      vaultError = false;
      const connection = await connect();
      announce(true);
      log("engine restarted");
      return connection;
    } catch {
      log("engine restart failed");
      announce(false);
      return null;
    }
  });
  const out = resolve(root, "out");
  protocol.handle("app", request => {
    const url = new URL(request.url);
    if (url.hostname !== "codeharness") return new Response("Forbidden", { status: 403 });
    let path: string;
    try { path = resolve(out, "." + decodeURIComponent(url.pathname)); }
    catch { return new Response("Bad path", { status: 400 }); }
    if (path !== out && !path.startsWith(out + sep)) return new Response("Forbidden", { status: 403 });
    if (existsSync(path) && statSync(path).isDirectory()) path = resolve(path, "index.html");
    if (!existsSync(path)) return new Response("Not found", { status: 404 });
    return net.fetch(pathToFileURL(path).href);
  });
  const window = new BrowserWindow({
    width: 1440, height: 960, minWidth: 800, minHeight: 600,
    backgroundColor: "#1F2125", title: "CodeHarness", autoHideMenuBar: true,
    webPreferences: { preload: resolve(__dirname, "preload.cjs"),
      nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith("app://codeharness/")) event.preventDefault();
  });
  window.webContents.on("render-process-gone", () => app.quit());
  await window.loadURL("app://codeharness/" + (process.env.CODEHARNESS_LANGUAGE === "en" ? "?lang=en" : ""));
});
app.on("before-quit", () => sidecar?.close());
app.on("window-all-closed", () => app.quit());
