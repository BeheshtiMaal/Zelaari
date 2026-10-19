import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomBytes, createCipheriv, createDecipheriv } from "node:crypto";
import { Vault, trustedFrame, modelSubmission, type Encryption } from "../../electron/vault";

test("vault persists ciphertext, retains keys, replaces keys and fails closed", async () => {
  const key = randomBytes(32), iv = randomBytes(16);
  const encryption: Encryption = {
    isEncryptionAvailable: () => true,
    encryptString(value) { const cipher = createCipheriv("aes-256-cbc", key, iv); return Buffer.concat([cipher.update(value), cipher.final()]); },
    decryptString(value) { const decipher = createDecipheriv("aes-256-cbc", key, iv); return Buffer.concat([decipher.update(value), decipher.final()]).toString(); },
  };
  const path = join(await mkdtemp(join(tmpdir(), "harness-vault-")), "vault.json");
  const canary = randomBytes(24).toString("hex");
  await new Vault(path, encryption).put("mine", canary);
  assert.ok(!(await readFile(path, "utf8")).includes(canary));
  const restored = new Vault(path, encryption);
  assert.equal((await restored.all()).mine, canary);
  await restored.put("mine", "replacement");
  assert.equal((await restored.all()).mine, "replacement");
  encryption.isEncryptionAvailable = () => false;
  await assert.rejects(restored.put("mine", canary), /Vault unavailable/);
  await assert.rejects(restored.all(), /Vault unavailable/);
});

test("IPC frame and model submission validation reject lookalikes and extra properties", () => {
  assert.ok(trustedFrame("app://codeharness/settings/"));
  for (const url of [undefined, "https://codeharness/", "app://codeharness.evil/", "app://user@codeharness/"]) assert.equal(trustedFrame(url), false);
  const valid = { id: "mine", name: "mine", model: "model", base_url: "https://api.example.invalid/v1" };
  assert.ok(modelSubmission.safeParse(valid).success);
  for (const extra of [{ price: 1 }, { api_key: "" }, { base_url: "https://user:secret@x" }, { id: "demo" }]) assert.equal(modelSubmission.safeParse({ ...valid, ...extra }).success, false);
});
