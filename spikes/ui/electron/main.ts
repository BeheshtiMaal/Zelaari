import { app, BrowserWindow, protocol, net } from "electron";
import { resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";

app.setPath("userData", mkdtempSync(resolve(tmpdir(), "codeharness-openui-")));
app.disableHardwareAcceleration();

protocol.registerSchemesAsPrivileged([{ scheme: "app", privileges: { standard: true, secure: true, supportFetchAPI: true } }]);
app.whenReady().then(async () => {
  const root = resolve(__dirname, "../out");
  protocol.handle("app", (request) => {
    const path = resolve(root, "." + decodeURIComponent(new URL(request.url).pathname === "/" ? "/index.html" : new URL(request.url).pathname));
    if (!path.startsWith(root + sep)) return new Response("Forbidden", { status: 403 });
    return net.fetch(pathToFileURL(path).href);
  });
  const win = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true } });
  if (process.env.SPIKE_PROTOCOL === "file") await win.loadFile(resolve(root, "index.html"));
  else await win.loadURL("app://spike/index.html");
});
app.on("window-all-closed", () => app.quit());
