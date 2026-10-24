import assert from "node:assert/strict";
import test from "node:test";
import { arcDash, barShare, compactTokens, percentLabel, ringLabel, usedPercent } from "../../src/lib/context-format";

test("token counts stay compact and localised", () => {
  assert.equal(compactTokens(0, "fa"), "۰");
  assert.equal(compactTokens(999, "fa"), "۹۹۹");
  assert.equal(compactTokens(1000, "fa"), "۱٫۰K");
  assert.equal(compactTokens(48800, "fa"), "۴۸٫۸K");
  assert.equal(compactTokens(128000, "fa"), "۱۲۸٫۰K");
  assert.equal(compactTokens(48800, "en"), "48.8K");
  assert.equal(compactTokens(Number.NaN, "en"), "0");
  assert.equal(compactTokens(-5, "en"), "0");
});

test("the fraction is clamped to a real share", () => {
  assert.equal(usedPercent(48800, 128000), 0.38125);
  assert.equal(usedPercent(200000, 128000), 1);
  assert.equal(usedPercent(-1, 128000), 0);
  assert.equal(usedPercent(10, null), 0);
  assert.equal(usedPercent(10, 0), 0);
});

test("the percentage keeps Persian digits and the percent sign", () => {
  assert.equal(percentLabel(0.38, "fa"), "۳۸٪");
  assert.equal(percentLabel(0.38, "en"), "38٪");
  assert.equal(percentLabel(1, "fa"), "۱۰۰٪");
});

test("the tooltip reads exactly like the mock", () => {
  assert.equal(ringLabel(48800, 128000, "fa", { used: false, window: false }), "۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K");
  assert.equal(ringLabel(48800, 128000, "en", { used: false, window: false }), "38٪ · 48.8K / 128.0K");
  // An estimate is marked, never passed off as a measurement.
  assert.equal(ringLabel(48800, 128000, "fa", { used: true, window: true }), "۳۸٪ · ~۴۸٫۸K / ~۱۲۸٫۰K");
  assert.equal(ringLabel(300, null, "fa", { used: false, window: false }), "۰٪ · ۳۰۰");
});

test("the arc dasharray follows the fraction and never overdraws", () => {
  const circumference = 2 * Math.PI * 14;
  assert.equal(arcDash(0).dashoffset, circumference);
  assert.equal(arcDash(1).dashoffset, 0);
  assert.equal(arcDash(0.5).dashoffset, circumference / 2);
  assert.equal(arcDash(1.4).dashoffset, 0);
  assert.equal(arcDash(-1).dashoffset, circumference);
  assert.equal(arcDash(0.38).dasharray, `${circumference} ${circumference}`);
});

test("row bars are a share of the whole, never negative", () => {
  assert.equal(barShare(10, 40), 0.25);
  assert.equal(barShare(50, 40), 1);
  assert.equal(barShare(10, 0), 0);
  assert.equal(barShare(-3, 40), 0);
});
