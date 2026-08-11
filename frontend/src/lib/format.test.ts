import { describe, expect, it } from "vitest";
import { dayKey, formatMoney, formatMonthLabel, formatShortMonth, shiftMonth } from "./format";

describe("formatMoney", () => {
  it("formats a positive amount with the currency symbol", () => {
    const result = formatMoney(1234.5, "EUR");
    expect(result).toContain("€");
    expect(result).toContain("50");
  });

  it("accepts a string amount, same as a number", () => {
    expect(formatMoney("100", "EUR")).toBe(formatMoney(100, "EUR"));
  });

  it("formats negative amounts with a minus sign", () => {
    const result = formatMoney(-50, "EUR");
    expect(result).toContain("-");
    expect(result).toContain("50,00");
  });
});

describe("dayKey", () => {
  it("extracts the YYYY-MM-DD prefix from an ISO datetime", () => {
    expect(dayKey("2026-03-15T10:30:00Z")).toBe("2026-03-15");
  });
});

describe("formatMonthLabel", () => {
  it("includes the month name and year", () => {
    const label = formatMonthLabel("2026-03").toLowerCase();
    expect(label).toContain("marzo");
    expect(label).toContain("2026");
  });
});

describe("formatShortMonth", () => {
  it("returns a short month label without a trailing dot", () => {
    const label = formatShortMonth("2026-03");
    expect(label).not.toContain(".");
    expect(label.length).toBeGreaterThan(0);
  });
});

describe("shiftMonth", () => {
  it("moves forward within the same year", () => {
    expect(shiftMonth("2026-03", 1)).toEqual({ year: 2026, month: 4 });
  });

  it("moves backward across a year boundary", () => {
    expect(shiftMonth("2026-01", -1)).toEqual({ year: 2025, month: 12 });
  });

  it("moves forward across a year boundary", () => {
    expect(shiftMonth("2026-12", 1)).toEqual({ year: 2027, month: 1 });
  });
});
