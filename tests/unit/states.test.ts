import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { statesCopy } from "../../src/i18n/states";
import { STATE_KEYS, WIRED, stateText } from "../../src/lib/states";

/**
 * The six empty states are a contract: each one has a label, a title, help text and one
 * primary action, in both languages, and each is either wired to a surface or recorded
 * as not wired. A state that quietly loses its action would be a dead card.
 */

const LOCALES = ["fa", "en"] as const;

describe("the six empty states", () => {
  it("are exactly the six the phase promises", () => {
    assert.deepEqual([...STATE_KEYS], ["noWorkspace", "noModel", "emptyInbox", "noSchedules", "noTasks", "noSkills"]);
  });

  for (const locale of LOCALES) {
    it(`have every part in ${locale}`, () => {
      const copy = statesCopy(locale);
      for (const key of STATE_KEYS) {
        const text = stateText(copy, key);
        for (const [part, value] of Object.entries(text)) {
          assert.equal(typeof value, "string", `${key}.${part} in ${locale}`);
          assert.ok(value.trim().length > 0, `${key}.${part} in ${locale} is empty`);
        }
      }
    });
  }

  it("offer a second, different way out of the two first-run states", () => {
    const en = statesCopy("en"), fa = statesCopy("fa");
    for (const copy of [en, fa]) {
      assert.notEqual(copy.noWorkspace.sample, copy.noWorkspace.primary);
      assert.notEqual(copy.noModel.demo, copy.noModel.primary);
      assert.ok(copy.noWorkspace.sample.length > 0);
      assert.ok(copy.noModel.demo.length > 0);
    }
  });

  it("say the same thing in both languages, key for key", () => {
    const shape = (value: object): string[] => Object.entries(value)
      .map(([key, item]) => typeof item === "object" && item !== null
        ? `${key}.${shape(item as object).join(",")}`
        : key)
      .sort();
    assert.deepEqual(shape(statesCopy("fa")), shape(statesCopy("en")));
  });

  it("are all wired to a surface except the one this build cannot reach", () => {
    const wired = STATE_KEYS.filter(key => WIRED[key] !== null);
    assert.equal(wired.length, 5);
    assert.equal(WIRED.noSchedules, null, "the schedules state is Phase 9b: no scheduler exists yet");
    assert.equal(WIRED.noWorkspace, "home");
    assert.equal(WIRED.noModel, "home");
    assert.equal(WIRED.emptyInbox, "inbox");
    assert.equal(WIRED.noTasks, "workspace");
    assert.equal(WIRED.noSkills, "customize/skills");
  });

  it("name the schedule state honestly instead of offering a button that does nothing", () => {
    for (const locale of LOCALES) {
      const text = statesCopy(locale).noSchedules;
      assert.ok(text.help.length > 0);
      assert.equal(/add|new|create|ساخت|افزودن/i.test(text.primary), false, text.primary);
    }
  });
});

describe("the crash card copy", () => {
  for (const locale of LOCALES) {
    it(`says what happened, what is safe and what to do in ${locale}`, () => {
      const crash = statesCopy(locale).crash;
      for (const part of ["title", "safe", "restart", "restarting", "failed", "logs", "notice"] as const) {
        assert.ok(crash[part].trim().length > 0, `crash.${part} in ${locale}`);
      }
      assert.notEqual(crash.restart, crash.logs, "the two actions must be distinguishable");
      assert.notEqual(crash.restart, crash.restarting);
    });
  }

  it("promises that the work is saved, because that is the question a person asks first", () => {
    for (const locale of LOCALES) {
      const safe = statesCopy(locale).crash.safe.toLowerCase();
      assert.ok(
        safe.includes("saved") || safe.includes("ذخیره"),
        `the safe line in ${locale} has to say the work is saved: ${safe}`,
      );
    }
  });
});
