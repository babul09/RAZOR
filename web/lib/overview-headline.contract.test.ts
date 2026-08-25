import test from "node:test";
import assert from "node:assert/strict";

function formatHeadline(incrementalPaise: number | null): string {
  if (incrementalPaise === null) return "comparison unavailable";
  const rupees = incrementalPaise / 100;
  const sign = rupees >= 0 ? "+" : "−";
  const amount = Math.abs(rupees) >= 100000
    ? `₹${(Math.abs(rupees) / 100000).toFixed(2)}L`
    : `₹${Math.round(Math.abs(rupees)).toLocaleString("en-IN")}`;
  return `${sign}${amount} incremental revenue`;
}

test("positive incremental value uses signed lakhs", () => {
  assert.equal(formatHeadline(72200000), "+₹7.22L incremental revenue");
});

test("zero and negative values preserve sign", () => {
  assert.equal(formatHeadline(0), "+₹0 incremental revenue");
  assert.equal(formatHeadline(-125000), "−₹1,250 incremental revenue");
});

test("absent comparison is explicit", () => {
  assert.equal(formatHeadline(null), "comparison unavailable");
  assert.doesNotMatch(formatHeadline(null), /7\.22L/);
});
