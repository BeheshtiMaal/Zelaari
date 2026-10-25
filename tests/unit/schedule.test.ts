import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { scheduleCopy } from "../../src/i18n/schedule";
import {
  dayLabel,
  effectiveMode,
  formatTime,
  inputFrom,
  isExpired,
  isMissed,
  lastResultLabel,
  nextRunLabel,
  recurrenceLabel,
  toSchedule,
  type Schedule,
} from "../../src/lib/schedule";
import type { ScheduleRecord } from "../../src/lib/protocol";

/**
 * The Schedule screen's rules, away from the screen.
 *
 * The six-cell permission table is checked here *and* in the engine. That duplication is
 * deliberate (D42): the dialog has to answer before a round trip and the engine has to
 * answer when a run starts. If the two ever disagree, the engine is right and this test is
 * the alarm.
 */

const NOW = "2026-10-25T12:00:00";
const en = scheduleCopy("en");
const fa = scheduleCopy("fa");

function record(overrides: Partial<ScheduleRecord> = {}): ScheduleRecord {
  return {
    id: "s1",
    name: "Nightly tests",
    prompt: "Run the tests",
    workspace: "C:/work/invoice-parser",
    model: "demo",
    created_at: "2026-10-20T12:00:00",
    next_run_at: "2026-10-26T02:00:00",
    time: "02:00",
    ...overrides,
  };
}

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return { ...toSchedule(record()), ...overrides };
}

describe("the permission table", () => {
  it("resolves all six cells", () => {
    assert.equal(effectiveMode("read-only", "report"), "read-only");
    assert.equal(effectiveMode("read-only", "full"), "read-only");
    assert.equal(effectiveMode("ask", "report"), "read-only");
    assert.equal(effectiveMode("ask", "full"), "ask");
    assert.equal(effectiveMode("auto", "report"), "read-only");
    assert.equal(effectiveMode("auto", "full"), "auto");
  });

  it("never lets a ceiling widen a mode", () => {
    const order = ["read-only", "ask", "auto"];
    for (const mode of ["read-only", "ask", "auto"] as const) {
      for (const ceiling of ["report", "full"] as const) {
        assert.ok(order.indexOf(effectiveMode(mode, ceiling)) <= order.indexOf(mode), `${mode}/${ceiling}`);
      }
    }
  });
});

describe("the wire defaults", () => {
  it("resolves every optional field the engine leaves out", () => {
    const resolved = toSchedule(record());
    assert.deepEqual(
      [resolved.mode, resolved.ceiling, resolved.repeat, resolved.weekday, resolved.enabled],
      ["read-only", "report", "daily", null, true],
    );
    assert.equal(resolved.lastStatus, null);
    assert.equal(resolved.lastError, null);
  });

  it("keeps an unknown status out of the union instead of trusting it", () => {
    assert.equal(toSchedule(record({ last_status: "exploded" as never })).lastStatus, null);
  });
});

describe("recurrence", () => {
  it("writes a nightly schedule the way the mock does", () => {
    assert.equal(recurrenceLabel(schedule(), en, "en"), "Every night at 02:00");
    assert.equal(recurrenceLabel(schedule(), fa, "fa"), "هر شب ساعت ۰۲:۰۰");
  });

  it("writes a weekly schedule with its day", () => {
    const weekly = schedule({ repeat: "weekly", weekday: 4, time: "09:00" });
    assert.equal(recurrenceLabel(weekly, en, "en"), "Fridays at 09:00");
    assert.equal(recurrenceLabel(weekly, fa, "fa"), "جمعه‌ها ساعت ۰۹:۰۰");
  });

  it("uses the reader's digits for a clock time", () => {
    assert.equal(formatTime("02:00", "fa"), "۰۲:۰۰");
    assert.equal(formatTime("02:00", "en"), "02:00");
    assert.equal(formatTime("23:59", "fa"), "۲۳:۵۹");
  });
});

describe("days", () => {
  it("names today, tomorrow and yesterday and dates the rest", () => {
    assert.equal(dayLabel("2026-10-25T02:00:00", NOW, "en", en), "today");
    assert.equal(dayLabel("2026-10-26T02:00:00", NOW, "en", en), "tomorrow");
    assert.equal(dayLabel("2026-10-24T02:00:00", NOW, "en", en), "yesterday");
    assert.match(dayLabel("2026-09-01T02:00:00", NOW, "en", en), /1 Sept?|Sep 1/);
  });

  it("crosses a month boundary without arithmetic slips", () => {
    assert.equal(dayLabel("2026-11-01T02:00:00", "2026-10-31T12:00:00", "en", en), "tomorrow");
    assert.equal(dayLabel("2026-10-31T02:00:00", "2026-11-01T12:00:00", "en", en), "yesterday");
  });

  it("says the same thing in Persian", () => {
    assert.equal(dayLabel("2026-10-25T02:00:00", NOW, "fa", fa), "امروز");
    assert.equal(dayLabel("2026-10-26T02:00:00", NOW, "fa", fa), "فردا");
    assert.equal(dayLabel("2026-10-24T02:00:00", NOW, "fa", fa), "دیشب");
  });
});

describe("the row's status", () => {
  it("puts a person waiting above any result", () => {
    const ran = schedule({ lastStatus: "completed", lastRunAt: "2026-10-24T02:00:00" });
    assert.deepEqual(lastResultLabel(ran, 2, NOW, en, "en"), { text: "2 approvals queued", tone: "warn" });
    assert.deepEqual(lastResultLabel(ran, 1, NOW, en, "en"), { text: "1 approval queued", tone: "warn" });
    assert.deepEqual(lastResultLabel(ran, 1, NOW, fa, "fa"), { text: "۱ تأیید در صف", tone: "warn" });
  });

  it("reports a missed occurrence before an old result", () => {
    const missed = schedule({
      lastStatus: "missed",
      missedAt: "2026-10-25T02:00:00",
      lastRunAt: "2026-10-24T02:00:00",
    });
    assert.deepEqual(lastResultLabel(missed, 0, NOW, en, "en"), { text: en.missed, tone: "warn" });
    assert.ok(isMissed(missed));
  });

  it("says a failure is a failure, not a blank", () => {
    const broken = schedule({ lastError: "The model is not available", lastStatus: "error" });
    assert.deepEqual(lastResultLabel(broken, 0, NOW, en, "en"), { text: en.error, tone: "danger" });
  });

  it("says nothing has run yet instead of inventing a time", () => {
    assert.deepEqual(lastResultLabel(schedule(), 0, NOW, en, "en"), { text: en.never, tone: "muted" });
  });

  it("reads a finished run as a day and a verdict", () => {
    const done = schedule({ lastStatus: "completed", lastRunAt: "2026-10-24T02:00:00" });
    assert.deepEqual(lastResultLabel(done, 0, NOW, en, "en"), {
      text: "Last run: yesterday · Succeeded",
      tone: "ok",
    });
    assert.equal(lastResultLabel(done, 0, NOW, fa, "fa").text, "آخرین اجرا: دیشب · موفق");
  });
});

describe("the next occurrence", () => {
  it("shows when it will run next", () => {
    assert.equal(nextRunLabel(schedule(), NOW, en, "en"), "Next run: tomorrow · 02:00");
    assert.equal(nextRunLabel(schedule(), NOW, fa, "fa"), "اجرای بعدی: فردا · ۰۲:۰۰");
  });

  it("says expired rather than showing a date that will never come", () => {
    const ended = schedule({ nextRunAt: null });
    assert.ok(isExpired(ended));
    assert.equal(nextRunLabel(ended, NOW, en, "en"), en.expired);
  });
});

describe("the dialog's prefill", () => {
  it("sends back exactly what it was given", () => {
    const source = schedule({
      mode: "ask",
      ceiling: "full",
      repeat: "weekly",
      weekday: 4,
      time: "09:00",
      validUntil: "2026-12-31",
      enabled: false,
    });
    assert.deepEqual(inputFrom(source), {
      name: source.name,
      prompt: source.prompt,
      workspace: source.workspace,
      model: source.model,
      mode: "ask",
      ceiling: "full",
      repeat: "weekly",
      weekday: 4,
      time: "09:00",
      valid_until: "2026-12-31",
      enabled: false,
    });
  });
});

describe("the templates", () => {
  it("are the six the mock draws, in both languages", () => {
    assert.equal(en.templates.length, 6);
    assert.equal(fa.templates.length, 6);
    assert.deepEqual(en.templates.map(item => item.id), [
      "nightly-tests",
      "git-review",
      "dependencies",
      "coverage",
      "todos",
      "weekly-summary",
    ]);
    assert.deepEqual(fa.templates.map(item => item.id), en.templates.map(item => item.id));
  });

  it("carry a name and a prompt a person could have typed", () => {
    for (const copy of [en, fa]) {
      for (const template of copy.templates) {
        assert.ok(template.name.trim().length > 0);
        assert.ok(template.prompt.trim().length > 0);
        assert.notEqual(template.name, template.prompt);
      }
    }
  });

  it("open on read-only and report, which is the unattended default", () => {
    assert.equal(effectiveMode("read-only", "report"), "read-only");
    assert.equal(en.modes["read-only"], "Read-only");
    assert.equal(en.ceilings.report, "Read-only and report");
  });
});
