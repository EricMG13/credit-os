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
    expect(page?.scatter.points).toHaveLength(12);
    expect(page?.scatter.points.map((p) => p.name).slice(1, 10)).toEqual(
      "ABCDEFGHI".split("").map((l) => `Holding ${l}`),
    );
    expect(page?.strips.rows[3]).toMatchObject({
      label: "Spread over benchmark",
      range: { low: 180, high: 520 },
      markers: [{ name: "TransDigm", value: null, text: null }],
    });
  });

  const L = [...F, "limits"] as const;
  const R = [...F, "ratings"] as const;
  const S = [...F, "scatter"] as const;
  const T = [...F, "strips"] as const;
  const xt = (axis: "x" | "y", i: number, key: string) => [...S, axis, "ticks", i, key] as const;

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
    [
      "a scale of zero",
      [...L, "columns", 0, "scaleMax"],
      0,
      `${P}.limits.columns[0].scaleMax: expected a number above zero`,
    ],
    [
      "a negative exposure",
      [...L, "columns", 0, "exposure"],
      -1,
      `${P}.limits.columns[0].exposure: expected a position from 0 to the scale (3.75)`,
    ],
    [
      "an exposure above the scale",
      [...L, "columns", 0, "exposure"],
      3.8,
      `${P}.limits.columns[0].exposure: expected a position from 0 to the scale (3.75)`,
    ],
    [
      "a limit above the scale",
      [...L, "columns", 1, "limit"],
      15.5,
      `${P}.limits.columns[1].limit: expected a position from 0 to the scale (15)`,
    ],
    [
      "a missing exposure with a text",
      [...L, "columns", 4, "exposureText"],
      "1%",
      `${P}.limits.columns[4].exposureText: expected null beside a missing exposure`,
    ],
    [
      "a present exposure without a text",
      [...L, "columns", 0, "exposureText"],
      null,
      `${P}.limits.columns[0].exposureText: expected a text beside a present exposure`,
    ],
    [
      "a missing limit with a text",
      [...L, "columns", 3, "limitText"],
      "limit 1%",
      `${P}.limits.columns[3].limitText: expected null beside a missing limit`,
    ],
    [
      "a present limit without a text",
      [...L, "columns", 0, "limitText"],
      null,
      `${P}.limits.columns[0].limitText: expected a text beside a present limit`,
    ],
    [
      "a table exposure that differs from the column's",
      [...L, "columns", 0, "cells", 0],
      "2.2%",
      `${P}.limits.columns[0].cells[0]: expected the column's exposure text`,
    ],
    [
      "a table limit that is not the column's limit without its word",
      [...L, "columns", 0, "cells", 1],
      "3.5%",
      `${P}.limits.columns[0].cells[1]: expected the column's limit text without its word`,
    ],
    [
      "a table limit beside a missing limit",
      [...L, "columns", 3, "cells", 1],
      "5%",
      `${P}.limits.columns[3].cells[1]: expected null beside a missing limit`,
    ],
    [
      "one table cell",
      [...L, "columns", 0, "cells"],
      ["2.1%"],
      `${P}.limits.columns[0].cells: expected 2 entries`,
    ],
    [
      "two ratings with one label",
      [...R, "tiles", 1, "label"],
      "Moody's, corporate family",
      `${P}.ratings.tiles[1].label: expected a label the other tile does not have`,
    ],
    [
      "three rating tiles",
      [...R, "tiles", 2],
      { label: "Fitch", value: null, caption: null },
      `${P}.ratings.tiles: expected 2 entries`,
    ],
    [
      "an empty reason",
      [...F, "relativeValue", "reason"],
      "",
      `${P}.relativeValue.reason: expected a non-empty string`,
    ],
    ["no point", [...S, "points"], [], `${P}.scatter.points: expected at least one point`],
    [
      "two points with one name",
      [...S, "points", 2, "name"],
      "Holding A",
      `${P}.scatter.points[2].name: expected a name no other point has`,
    ],
    [
      "two emphasised points",
      [...S, "points", 1, "emphasis"],
      true,
      `${P}.scatter.points[1].emphasis: expected at most one emphasised point`,
    ],
    [
      "the others' name on the issuer",
      [...S, "othersName"],
      "TransDigm",
      `${P}.scatter.othersName: expected a name the emphasised point does not have`,
    ],
    [
      "one x tick",
      [...S, "x", "ticks"],
      [{ value: 2, label: "2x" }],
      `${P}.scatter.x.ticks: expected at least two ticks, rising`,
    ],
    [
      "x ticks that do not rise",
      xt("x", 1, "value"),
      2,
      `${P}.scatter.x.ticks: expected at least two ticks, rising`,
    ],
    [
      "y ticks that do not rise",
      xt("y", 2, "value"),
      0,
      `${P}.scatter.y.ticks: expected at least two ticks, rising`,
    ],
    [
      "an x outside the axis",
      [...S, "points", 1, "x"],
      9,
      `${P}.scatter.points[1].x: expected a position from 2 to 8`,
    ],
    [
      "a y outside the axis",
      [...S, "points", 1, "y"],
      61,
      `${P}.scatter.points[1].y: expected a position from 0 to 60`,
    ],
    [
      "a missing y with a text",
      [...S, "points", 10, "yText"],
      "1%",
      `${P}.scatter.points[10].yText: expected null beside a missing y`,
    ],
    [
      "a present x without a text",
      [...S, "points", 1, "xText"],
      null,
      `${P}.scatter.points[1].xText: expected a text beside a present x`,
    ],
    [
      "a scatter table of two headings",
      [...S, "head"],
      ["Issuer", "Net leverage"],
      `${P}.scatter.head: expected 3 headings: the label, the x and the y`,
    ],
    [
      "a scatter cell that differs from the point's text",
      [...S, "points", 1, "cells", 1],
      "53.0%",
      `${P}.scatter.points[1].cells[1]: expected the point's y text`,
    ],
    ["no strip row", [...T, "rows"], [], `${P}.strips.rows: expected at least one row`],
    [
      "two strip rows with one label",
      [...T, "rows", 1, "label"],
      "Net leverage",
      `${P}.strips.rows[1].label: expected a label no other row has`,
    ],
    [
      "a row without a marker",
      [...T, "rows", 0, "markers"],
      [],
      `${P}.strips.rows[0].markers: expected at least one marker`,
    ],
    [
      "a marker named differently from the first row's",
      [...T, "rows", 1, "markers", 0, "name"],
      "Issuer",
      `${P}.strips.rows[1].markers[0].name: expected the names the first row's markers have, in order`,
    ],
    [
      "two markers with one name",
      [...T, "rows", 0, "markers"],
      [
        { name: "TransDigm", value: 5.9, text: "5.9x" },
        { name: "TransDigm", value: 5.9, text: "5.9x" },
      ],
      `${P}.strips.rows[0].markers[1].name: expected a name no other marker in the row has`,
    ],
    [
      "a range with its low above its high",
      [...T, "rows", 0, "range", "low"],
      7,
      `${P}.strips.rows[0].range: expected a low that is not above the high`,
    ],
    [
      "an axis whose max is its min",
      [...T, "rows", 0, "axis", "max"],
      0,
      `${P}.strips.rows[0].axis: expected a max above the min`,
    ],
    [
      "a range outside the axis",
      [...T, "rows", 0, "range", "high"],
      9,
      `${P}.strips.rows[0].range: expected a position from 0 to 8`,
    ],
    [
      "a marker outside the axis",
      [...T, "rows", 0, "markers", 0, "value"],
      8.5,
      `${P}.strips.rows[0].markers[0].value: expected a position from 0 to 8`,
    ],
    [
      "a missing marker with a text",
      [...T, "rows", 3, "markers", 0, "text"],
      "n.a.",
      `${P}.strips.rows[3].markers[0].text: expected null beside a missing value`,
    ],
    [
      "a present marker without a text",
      [...T, "rows", 0, "markers", 0, "text"],
      null,
      `${P}.strips.rows[0].markers[0].text: expected a text beside a present value`,
    ],
    [
      "a marker beside no range",
      [...T, "rows", 0, "range"],
      null,
      `${P}.strips.rows[0].markers[0].value: expected null beside a missing range`,
    ],
    [
      "a strip row with two cells",
      [...T, "rows", 0, "cells"],
      ["2.4x", "6.8x"],
      `${P}.strips.rows[0].cells: expected 3 cells, one per column after the label`,
    ],
    [
      "a range label equal to a marker name",
      [...T, "rangeLabel"],
      "TransDigm",
      `${P}.strips.rangeLabel: expected a label no marker has`,
    ],
    [
      "a strip table without a heading",
      [...T, "head"],
      [],
      `${P}.strips.head: expected a heading for the label column`,
    ],
    [
      "a scatter titled like the limits chart",
      [...S, "title"],
      "Exposure against limits",
      `${P}.scatter.title: expected a name no other trace control on the page has`,
    ],
    [
      "the strips chart titled like the ratings",
      [...T, "title"],
      "Agency ratings",
      `${P}.strips.title: expected a name no other trace control on the page has`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});

describe("the portfolio fit page: the table side holds to the chart side", () => {
  const R = [...F, "strips", "rows"] as const;
  const L = [...F, "limits", "columns"] as const;
  it.each<[string, readonly (string | number)[], unknown, string]>([
    [
      "a missing marker with a figure in its cell",
      [...R, 3, "cells"],
      ["180 bp", "520 bp", "350 bp"],
      `${P}.strips.rows[3].cells[2]: expected null beside a missing marker`,
    ],
    [
      "a marker with a text and n.a. in its cell",
      [...R, 0, "cells"],
      ["2.4x", "6.8x", null],
      `${P}.strips.rows[0].cells[2]: expected the text of marker 1, "5.9x", not n.a.`,
    ],
    [
      "a marker whose cell holds another text",
      [...R, 1, "cells"],
      ["1.6x", "6.2x", "3.0x"],
      `${P}.strips.rows[1].cells[2]: expected the text of marker 1, "2.9x"`,
    ],
    [
      "a limit word alone beside a table cell that is n.a.",
      [...L, 0],
      {
        label: "Single issuer",
        exposure: 2.1,
        limit: 3,
        scaleMax: 3.75,
        exposureText: "2.1%",
        limitText: "limit ",
        cells: ["2.1%", null],
      },
      `${P}.limits.columns[0].cells[1]: expected the column's limit text without its word`,
    ],
    [
      "a limit cell with no limit drawn",
      [...L, 3, "cells"],
      ["58.0%", "35.0%"],
      `${P}.limits.columns[3].cells[1]: expected null beside a missing limit`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});
