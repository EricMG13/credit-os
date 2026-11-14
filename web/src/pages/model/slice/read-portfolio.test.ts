import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const F = ["runs", 0, "portfolioFit"] as const;
const P = "runs[0].portfolioFit";

describe("the portfolio fit page of the slice", () => {
  it("reads the fixture as the mock draws it", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    const page = result.data.runs[0]?.portfolioFit;
    expect(page?.limits.columns.map((c) => [c.label, c.exposureText, c.limitText])).toEqual([
      ["Single issuer", "2.1%", "limit 3.0%"],
      ["Aerospace and defence", "9.4%", "limit 12.0%"],
      ["Rated single B", "31.0%", "limit 35.0%"],
      ["United States", "58.0%", null],
      ["Subordinated debt", null, "limit 10.0%"],
    ]);
    expect(page?.ratings.tiles.map((t) => [t.label, t.value, t.caption])).toEqual([
      ["Moody's, corporate family", "B1", "Stable outlook"],
      ["S&P, issuer credit", "B+", "Stable outlook"],
    ]);
    expect(page?.relativeValue.part).toBe("Spread against holdings");
  });

  const L = [...F, "limits"] as const;

  it.each<[string, readonly (string | number)[], unknown, string]>([
    ["an unknown key", [...F, "extra"], 1, `${P}.extra: unknown field`],
    [
      "an empty trace",
      [...L, "trace"],
      "",
      `${P}.limits.trace: expected a non-empty string or null`,
    ],
    ["no limit column", [...L, "columns"], [], `${P}.limits.columns: expected at least one column`],
    [
      "two limit columns with one label",
      [...L, "columns", 1, "label"],
      "Single issuer",
      `${P}.limits.columns[1].label: expected a label no other column has`,
    ],
    [
      "a limit table heading of two",
      [...L, "head"],
      ["Limit", "Exposure"],
      `${P}.limits.head: expected 3 headings: the label, the exposure and the limit`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});
