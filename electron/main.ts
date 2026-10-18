import { app, BrowserWindow, dialog, ipcMain, net, protocol } from "electron";
import { existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";
import { startSidecar, type Sidecar } from "./sidecar";
import { loadProviderConfig } from "./provider-config";

app.disableHardwareAcceleration();
protocol.registerSchemesAsPrivileged([{ scheme: "app", privileges: {
  standard: true, secure: true, supportFetchAPI: true,
} }]);
if (process.env.CODEHARNESS_TEST_USER_DATA) app.setPath("userData", process.env.CODEHARNESS_TEST_USER_DATA);
const root = app.isPackaged ? process.resourcesPath : resolve(__dirname, "..");
let sidecar: Sidecar | undefined;

app.whenReady().then(async () => {
  loadProviderConfig();
  // Keep the native window responsive during cold Python imports.
  ipcMain.on("engine-connection", (event) => {
    if (!event.senderFrame?.url.startsWith("app://codeharness/")) {
      event.returnValue = { baseUrl: "", token: "" };
      return;
    }
    sidecar ??= startSidecar(root, app.isPackaged, () => {
      for (const window of BrowserWindow.getAllWindows()) window.destroy();
      app.quit();
    });
    void sidecar!.ready.then(connection => { event.returnValue = connection; }, () => {
      event.returnValue = { baseUrl: "", token: "" };
    });
  });
  ipcMain.handle("pick-workspace", async (event) => {
    if (!event.senderFrame?.url.startsWith("app://codeharness/")) return null;
    const result = await dialog.showOpenDialog({ properties: ["openDirectory"] });
    return result.canceled ? null : result.filePaths[0] ?? null;
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
