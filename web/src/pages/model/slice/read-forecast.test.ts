import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const F = ["runs", 0, "forecast"] as const;
const P = "runs[0].forecast";
const D = [...F, "drivers"] as const;
const I = [...F, "interestCover"] as const;

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
    expect(page?.interestCover.cases.map((c) => c.values)).toEqual([
      [2.6, null, 2.8, 2.9, 3.0, 3.3, 3.6],
      [2.6, null, 2.8, 2.9, 2.9, 2.3, 2.4],
    ]);
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
      "an interest cover chart titled like the drivers chart",
      [...I, "title"],
      "What drives each case",
      `${P}.interestCover.title: expected a name no other trace control on the page has`,
    ],
    [
      "one interest cover line",
      [...I, "cases"],
      [
        {
          values: [2.6, null, 2.8, 2.9, 3.0, 3.3, 3.6],
          labels: [null, null, null, null, null, null, null],
        },
      ],
      `${P}.interestCover.cases: expected 2 lines, one per case`,
    ],
    [
      "an interest cover line with six values",
      [...I, "cases", 1, "values"],
      [2.6, null, 2.8, 2.9, 2.9, 2.3],
      `${P}.interestCover.cases[1].values: expected 7 entries, one per period`,
    ],
    [
      "an interest cover line with six labels",
      [...I, "cases", 1, "labels"],
      ["2.6x", null, "2.8x", "2.9x", "2.9x", "2.3x"],
      `${P}.interestCover.cases[1].labels: expected 7 entries, one per period`,
    ],
    [
      "a label beside a missing interest cover point",
      [...I, "cases", 0, "labels", 1],
      "2.7x",
      `${P}.interestCover.cases[0].labels[1]: expected null beside a missing value`,
    ],
    [
      "a point above the interest cover axis",
      [...I, "cases", 0, "values", 6],
      4.5,
      `${P}.interestCover.cases[0].values[6]: expected a position within the axis (0 to 4)`,
    ],
    [
      "a negative interest cover point",
      [...I, "cases", 0, "values", 0],
      -1,
      `${P}.interestCover.cases[0].values[0]: expected a position within the axis (0 to 4)`,
    ],
    [
      "a label unlike the table's text",
      [...I, "cases", 0, "labels", 0],
      "2.5x",
      `${P}.interestCover.cases[0].labels[0]: expected the table's text for this point`,
    ],
    [
      "a table cell present where the point is missing",
      [...I, "rows", 0, "cells", 1],
      "2.7x",
      `${P}.interestCover.rows[0].cells[1]: expected null exactly where the point is missing`,
    ],
    [
      "a table cell missing where the point is present",
      [...I, "rows", 1, "cells", 0],
      null,
      `${P}.interestCover.rows[1].cells[0]: expected null exactly where the point is missing`,
    ],
    [
      "one interest cover table row",
      [...I, "rows"],
      [{ label: "Base case", cells: ["2.6x", null, "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"] }],
      `${P}.interestCover.rows: expected 2 rows, one per case`,
    ],
    [
      "an interest cover table row of six cells",
      [...I, "rows", 0, "cells"],
      ["2.6x", null, "2.8x", "2.9x", "3.0x", "3.3x"],
      `${P}.interestCover.rows[0].cells: expected 7 cells, one per period`,
    ],
    [
      "interest cover columns that are not the periods",
      [...I, "head", 2],
      "FY24",
      `${P}.interestCover.head: expected the periods after the first heading, in order`,
    ],
    [
      "a divider on a period the chart lacks",
      [...I, "divider", "period"],
      "FY28E",
      `${P}.interestCover.divider.period: expected one of the periods`,
    ],
    [
      "a divider after the last period",
      [...I, "divider"],
      { period: "FY27E", at: "after", label: "Forecast" },
      `${P}.interestCover.divider: expected a period after FY27E`,
    ],
    [
      "interest cover ticks that start above zero",
      [...I, "yTicks", 0, "value"],
      1,
      `${P}.interestCover.yTicks[0].value: expected the first tick to be 0`,
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
