import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const F = ["runs", 0, "forecast"] as const;
const P = "runs[0].forecast";
const D = [...F, "drivers"] as const;

describe("the forecast page of the slice", () => {
  it("reads the fixture as the mock draws it", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(`${result.kind}: ${JSON.stringify(result)}`);
    const page = result.data.runs[0]?.forecast;
    expect(page?.tabs.map((t) => [t.label, t.count, t.current])).toEqual([
      ["Overview", null, false],
      ["Changes", "5", false],
      ["Modules", "11", false],
      ["Forecast", null, true],
      ["Evidence", null, false],
    ]);
    expect(page?.periods).toEqual(["FY22", "FY23", "FY24", "LTM", "FY25E", "FY26E", "FY27E"]);
    expect(page?.drivers.rows.map((r) => [r.label, r.rangeText])).toEqual([
      ["Organic revenue growth", "Past five years: -12% to 18%"],
      ["EBITDA margin", "Past five years: 44% to 53%"],
      ["Capital expenditure, share of revenue", "Past five years: 1.6% to 2.4%"],
      ["Cash interest rate on debt", "Past five years: 5.2% to 7.1%"],
      ["Working capital days", "Past five years: 92 to 118"],
      ["Aftermarket share of revenue", "Range n.a."],
    ]);
    expect(page?.driverKeys).toEqual([
      { label: "Base case assumption", case: "Base case" },
      { label: "Downside case assumption", case: "Downside case" },
    ]);
    expect(page?.drivers.rows[4]?.markers).toEqual([
      { name: "Base case assumption", value: null, text: null },
      { name: "Downside case assumption", value: null, text: null },
    ]);
    expect(page?.drivers.rows[5]).toMatchObject({
      range: null,
      markers: [
        { name: "Base case assumption", value: 55, text: "55%" },
        { name: "Downside case assumption", value: 52, text: "52%" },
      ],
    });
    expect(page?.gap.title).toBe("Quarterly cash flow");
    expect(page?.watch.title).toBe("What would change the forecast");
    expect(page?.limitations.title).toBe("Limitations of the forecast");
  });

  it.each<[string, readonly (string | number)[], unknown, string]>([
    ["an unknown key", [...F, "extra"], 1, `${P}.extra: unknown field`],
    ["no tabs", [...F, "tabs"], [], `${P}.tabs: expected exactly one current tab`],
    [
      "an empty tab address",
      [...F, "tabs", 1, "href"],
      "",
      `${P}.tabs[1].href: expected a non-empty string`,
    ],
    [
      "an empty count",
      [...F, "tabs", 1, "count"],
      "",
      `${P}.tabs[1].count: expected a non-empty string or null`,
    ],
    [
      "two current tabs",
      [...F, "tabs", 0, "current"],
      true,
      `${P}.tabs: expected exactly one current tab`,
    ],
    [
      "two tabs with one label",
      [...F, "tabs", 1, "label"],
      "Overview",
      `${P}.tabs[1].label: expected a label no other tab has`,
    ],
    ["no periods", [...F, "periods"], [], `${P}.periods: expected at least one period`],
    [
      "a repeated period",
      [...F, "periods", 1],
      "FY22",
      `${P}.periods[1]: expected a period no other has`,
    ],
    [
      "a driver marker named as its row's first marker",
      [...D, "rows", 0, "markers", 1, "name"],
      "Base case assumption",
      `${P}.drivers.rows[0].markers[1].name: expected a name no other marker has`,
    ],
    [
      "a driver marker named otherwise than the first row's",
      [...D, "rows", 1, "markers", 1, "name"],
      "Stress case assumption",
      `${P}.drivers.rows[1].markers[1].name: expected the name the first row gives marker 2, "Downside case assumption"`,
    ],
    [
      "a driver legend entry belonging to the other case",
      [...F, "driverKeys", 0, "case"],
      "Downside case",
      `${P}.driverKeys[0].case: expected the name of case 1, "Base case"`,
    ],
    [
      "a driver legend entry worded otherwise than its marker",
      [...F, "driverKeys", 1, "label"],
      "Stress case assumption",
      `${P}.driverKeys[1].label: expected the name the markers give marker 2, "Downside case assumption"`,
    ],
    [
      "one driver legend entry",
      [...F, "driverKeys"],
      [{ label: "Base case assumption", case: "Base case" }],
      `${P}.driverKeys: expected 2 entries, one per case`,
    ],
    [
      "a driver with one marker",
      [...D, "rows", 0, "markers"],
      [{ name: "Base case assumption", value: 8, text: "8.0%" }],
      `${P}.drivers.rows[0].markers: expected 2 markers, one per case`,
    ],
    [
      "a driver row with the downside marker missing and the base present",
      [...D, "rows", 0, "markers", 1],
      { name: "Downside case assumption", value: null, text: null },
      `${P}.drivers.rows[0].markers[1].value: expected every marker of a row present, or every one missing`,
    ],
    [
      "a driver marker outside its axis",
      [...D, "rows", 0, "markers", 0, "value"],
      25,
      `${P}.drivers.rows[0].markers[0].value: expected a position from -15 to 20`,
    ],
    [
      "a driver marker with a value and no text",
      [...D, "rows", 5, "markers", 0, "text"],
      null,
      `${P}.drivers.rows[5].markers[0].text: expected a text beside a present value`,
    ],
    [
      "a driver range that is neither null nor a low and a high",
      [...D, "rows", 0, "range"],
      { wrong: true },
      `${P}.drivers.rows[0].range: expected null or an object with low and high`,
    ],
    [
      "a driver range above its axis",
      [...D, "rows", 1, "range"],
      { low: 44, high: 60 },
      `${P}.drivers.rows[1].range: expected a position from 40 to 56`,
    ],
    [
      "a drivers table head naming the cases in the other order",
      [...D, "head", 3],
      "Downside case",
      `${P}.drivers.head[3]: expected the name of case 1, "Base case"`,
    ],
    [
      "a drivers table head whose last column is no case",
      [...D, "head", 4],
      "Stress case",
      `${P}.drivers.head[4]: expected the name of case 2, "Downside case"`,
    ],
    [
      "a driver row with three cells",
      [...D, "rows", 0, "cells"],
      ["-12%", "18%", "8.0%"],
      `${P}.drivers.rows[0].cells: expected 4 cells, one per column after the label`,
    ],
    [
      "a passage titled like a case",
      [...F, "watch", "title"],
      "Base case",
      `${P}.watch.title: expected a name no other trace control on the page has`,
    ],
    [
      "an empty gap reason",
      [...F, "gap", "reason"],
      "",
      `${P}.gap.reason: expected a non-empty string`,
    ],
    [
      "an empty gap title",
      [...F, "gap", "title"],
      "",
      `${P}.gap.title: expected a non-empty string`,
    ],
    [
      "an empty watch trace",
      [...F, "watch", "trace"],
      "",
      `${P}.watch.trace: expected a non-empty string or null`,
    ],
    [
      "a limitations link without an address",
      [...F, "limitations", "href"],
      "",
      `${P}.limitations.href: expected a non-empty string`,
    ],
    [
      "a limitations item without its sentence",
      [...F, "limitations", "text"],
      "",
      `${P}.limitations.text: expected a non-empty string`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});

describe("the forecast page: the table side holds to the chart side", () => {
  it("refuses a driver's case cells swapped against its markers, naming the first", () => {
    expect(readSlice(edited([...D, "rows", 0, "cells"], ["-12%", "18%", "-4.0%", "8.0%"]))).toEqual(
      {
        kind: "invalid",
        reason: `${P}.drivers.rows[0].cells[2]: expected the text of marker 1, "8.0%"`,
      },
    );
  });

  it("refuses a driver cell that is n.a. beside a marker with a text, and the reverse", () => {
    expect(readSlice(edited([...D, "rows", 0, "cells"], ["-12%", "18%", null, "-4.0%"]))).toEqual({
      kind: "invalid",
      reason: `${P}.drivers.rows[0].cells[2]: expected the text of marker 1, "8.0%", not n.a.`,
    });
    expect(readSlice(edited([...D, "rows", 4, "cells"], ["92", "118", "5", null]))).toEqual({
      kind: "invalid",
      reason: `${P}.drivers.rows[4].cells[2]: expected null beside a missing marker`,
    });
  });
});
