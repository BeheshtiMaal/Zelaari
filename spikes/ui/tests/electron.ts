import { _electron as electron, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

await mkdir("../artifacts", { recursive: true });
const results: object[] = [];
for (const protocol of ["file", "app"]) {
  const instance = await electron.launch({ args: [resolve("electron/main.cjs")], env: { ...process.env, SPIKE_PROTOCOL: protocol } });
  const errors: string[] = [];
  try {
    const page = await instance.firstWindow();
    page.on("pageerror", error => errors.push(error.message));
    page.on("requestfailed", request => errors.push(request.url() + ": " + request.failure()?.errorText));
    await expect(page.getByRole("heading")).toHaveText("OpenUI technical spike");
    await expect(page.locator('main[data-hydrated="true"]')).toBeVisible();
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(21, 22, 24)");
    await page.getByRole("button", { name: "Start", exact: true }).click();
    await expect(page.getByTestId("callout")).toContainText("Hel").catch(async error => {
      throw new Error(String(error) + "\nDiagnostics: " + await page.getByTestId("diagnostics").textContent());
    });
    await page.getByRole("button", { name: "Chunk", exact: true }).click();
    await expect(page.getByTestId("callout")).toHaveText("Hello");
    await page.getByRole("button", { name: "Finish", exact: true }).click();
    await expect(page.getByTestId("keyvalue")).toContainText("Ready");
    await expect(page.getByTestId("stack")).toBeVisible();
    await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await expect(page.getByTestId("fallback")).toHaveCount(0);
    await expect(page.getByTestId("keyvalue")).toContainText("Ready");
    for (const component of ["Callout", "Stack", "KeyValue"]) await expect(page.getByTestId("prompt")).toContainText(component);
    await page.screenshot({ path: `../artifacts/openui-${protocol}.png` });
    await page.getByRole("button", { name: "Malformed", exact: true }).click();
    await expect(page.getByTestId("fallback")).toContainText("bad input");
    await page.screenshot({ path: `../artifacts/openui-${protocol}-fallback.png` });
    expect(errors).toEqual([]);
    results.push({ protocol, passed: true, errors });
  } finally { await instance.close(); }
}
await writeFile("../artifacts/openui.json", JSON.stringify(results, null, 2));
console.log("OpenUI: both protocols, progressive rendering, prompt and fallback passed");
