import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SCOPES, SHORTCUTS, isTyping, resolve, rowsFor, shortcutDigit } from "../../src/lib/shortcuts";
import { scopeCopy, shortcutsCopy } from "../../src/i18n/shortcuts";
import { keyAction, reviewShortcut } from "../../src/lib/approvals";

/**
 * The keyboard contract is data, so these tests read the table instead of restating it.
 *
 * A shortcut that exists in a handler but not in the table is exactly the drift R14 forbids,
 * so every assertion below goes through `resolve` — the same function the components call.
 */

const press = (key: string, extra: Partial<Parameters<typeof resolve>[1]> = {}) => ({ key, ...extra });

describe("the table", () => {
  it("answers for every scope and nothing else", () => {
    const covered = new Set(SHORTCUTS.map(row => row.scope));
    assert.deepEqual([...covered].sort(), [...SCOPES].sort());
    assert.equal(resolve("dialog", press("Enter")), null, "a dialog has no opinion on Enter");
  });

  it("documents every row with a key and a sentence in both locales", () => {
    for (const row of SHORTCUTS) {
      assert.ok(row.keys.trim().length > 0, `${row.scope}/${row.action} has no key`);
      assert.ok(shortcutsCopy("fa")[row.copy].trim().length > 0, `${row.copy} has no Persian sentence`);
      assert.ok(shortcutsCopy("en")[row.copy].trim().length > 0, `${row.copy} has no English sentence`);
    }
  });

  it("names every scope for a help surface", () => {
    for (const scope of SCOPES) {
      assert.ok(scopeCopy("fa")[scope].trim().length > 0);
      assert.ok(scopeCopy("en")[scope].trim().length > 0);
    }
  });

  it("lists rows in one scope in table order, so the specific key can come first", () => {
    const composer = rowsFor("composer").map(row => row.action);
    assert.deepEqual(composer, ["newline", "send", "command", "mention", "dismiss"]);
  });
});

describe("the composer", () => {
  it("sends on Enter and adds a line on Shift+Enter", () => {
    assert.deepEqual(resolve("composer", press("Enter")), { action: "send" });
    assert.deepEqual(resolve("composer", press("Enter", { shiftKey: true })), { action: "newline" });
  });

  it("opens the pickers and dismisses them", () => {
    assert.deepEqual(resolve("composer", press("/")), { action: "command" });
    assert.deepEqual(resolve("composer", press("@")), { action: "mention" });
    assert.deepEqual(resolve("composer", press("Escape")), { action: "dismiss" });
  });

  it("leaves a modified Enter to the operating system", () => {
    assert.equal(resolve("composer", press("Enter", { metaKey: true })), null);
    assert.equal(resolve("composer", press("Enter", { ctrlKey: true })), null);
    assert.equal(resolve("composer", press("Enter", { altKey: true })), null);
  });
});

describe("a question card", () => {
  const three = { optionCount: 3 };

  it("picks an option by its number", () => {
    assert.deepEqual(resolve("questions", press("1"), three), { action: "pick", index: 0 });
    assert.deepEqual(resolve("questions", press("3", { code: "Digit3" }), three), { action: "pick", index: 2 });
  });

  it("reaches the free-text answer with the next number", () => {
    assert.deepEqual(resolve("questions", press("4"), three), { action: "other" });
    assert.deepEqual(resolve("questions", press("4"), { optionCount: 4 }), { action: "pick", index: 3 }, "with four options the fourth number picks the fourth");
    assert.equal(resolve("questions", press("5"), { optionCount: 4 }), null, "a fifth number is past the table");
  });

  it("ignores a number past the options and past four", () => {
    assert.equal(resolve("questions", press("4"), { optionCount: 2 }), null);
    assert.equal(resolve("questions", press("5"), { optionCount: 2 }), null);
  });

  it("reads a Persian digit from the keyboard the person is using", () => {
    assert.equal(shortcutDigit({ key: "۲" }), 2);
    assert.equal(shortcutDigit({ key: "۳", code: "Digit3" }), 3, "the physical key wins over the layout");
    assert.ok(Number.isNaN(shortcutDigit({ key: "a" })));
  });

  it("advances on Enter and declines on Escape", () => {
    assert.deepEqual(resolve("questions", press("Enter"), three), { action: "advance" });
    assert.deepEqual(resolve("questions", press("Escape"), three), { action: "decline" });
    assert.equal(resolve("questions", press("Enter", { tag: "BUTTON" }), three), null, "Enter on a button presses the button");
  });

  it("does nothing while the person is writing the free-text answer", () => {
    assert.equal(resolve("questions", press("Enter", { tag: "INPUT" }), three), null);
    assert.equal(resolve("questions", press("1", { tag: "TEXTAREA" }), three), null);
    assert.equal(resolve("questions", press("Escape", { contentEditable: true }), three), null);
  });
});

describe("an approval card", () => {
  it("approves on Enter and rejects on Escape", () => {
    assert.deepEqual(resolve("approval", press("Enter")), { action: "approve" });
    assert.deepEqual(resolve("approval", press("Escape")), { action: "reject" });
  });

  it("leaves the decision alone when the focus is in a field or on a button", () => {
    assert.equal(resolve("approval", press("Enter", { tag: "INPUT" })), null);
    assert.equal(resolve("approval", press("Enter", { tag: "BUTTON" })), null, "Enter on a button presses the button");
    assert.equal(resolve("approval", press("Escape", { tag: "TEXTAREA" })), null);
  });

  it("keeps the older entry points answering from the same table", () => {
    assert.equal(keyAction("Enter"), "approve");
    assert.equal(keyAction("Escape"), "reject");
    assert.equal(keyAction("a"), null);
    assert.equal(reviewShortcut("Enter", "BUTTON"), null);
    assert.equal(reviewShortcut("Escape", "INPUT"), null);
    assert.equal(reviewShortcut("Enter", "SECTION"), "approve");
  });
});

describe("the inbox list", () => {
  it("moves with the arrows and with j/k", () => {
    assert.deepEqual(resolve("inbox", press("ArrowDown")), { action: "next" });
    assert.deepEqual(resolve("inbox", press("ArrowUp")), { action: "previous" });
    assert.deepEqual(resolve("inbox", press("j")), { action: "next" });
    assert.deepEqual(resolve("inbox", press("k")), { action: "previous" });
  });

  it("does not steal a key from a field", () => {
    assert.equal(resolve("inbox", press("j", { tag: "INPUT" })), null);
    assert.equal(resolve("inbox", press("ArrowDown", { tag: "SELECT" })), null);
  });
});

describe("any dialog", () => {
  it("closes on Escape and ignores everything else", () => {
    assert.deepEqual(resolve("dialog", press("Escape")), { action: "close" });
    assert.deepEqual(resolve("dialog", press("Escape", { tag: "INPUT" })), { action: "close" }, "Escape closes the dialog even from a field in it");
  });
});

describe("the typing rule", () => {
  it("covers fields and contenteditable, and nothing else", () => {
    for (const tag of ["INPUT", "TEXTAREA", "SELECT"]) assert.ok(isTyping({ key: "a", tag }));
    assert.ok(isTyping({ key: "a", contentEditable: true }));
    for (const tag of ["BUTTON", "SECTION", "DIV", undefined]) assert.equal(isTyping({ key: "a", tag }), false);
  });
});
