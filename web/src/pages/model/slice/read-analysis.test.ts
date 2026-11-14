import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const A = ["runs", 0, "analysis"] as const;
const P = "runs[0].analysis";

describe("the analysis page of the slice", () => {
  it("reads the fixture as the mock draws it", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    const page = result.data.runs[0]?.analysis;
    expect(page?.findings.map((f) => f.number)).toEqual(["01", "02", "03", "04"]);
    expect(page?.measures.stats.map((s) => s.value)).toEqual(["5.9x", "2.9x", "6.6%", null]);
    expect(page?.headroom.rows[3]).toMatchObject({ value: null, target: 7.25, text: null });
    expect(page?.segments.rows[3]).toMatchObject({ from: null, to: 44, text: "n.a. to 44.0%" });
    expect(page?.limitations).toMatchObject({
      count: "2 of 6",
      linkText: "See all six limitations",
    });
  });

  it.each<[string, readonly (string | number)[], unknown, string]>([
    ["an unknown key", [...A, "extra"], 1, `${P}.extra: unknown field`],
    ["no finding", [...A, "findings"], [], `${P}.findings: expected at least one finding`],
    [
      "two findings with one number",
      [...A, "findings", 1, "number"],
      "01",
      `${P}.findings[1].number: expected a number no other finding has`,
    ],
    [
      "an empty finding title",
      [...A, "findings", 0, "title"],
      "",
      `${P}.findings[0].title: expected a non-empty string`,
    ],
    [
      "an empty trace",
      [...A, "findings", 0, "trace"],
      "",
      `${P}.findings[0].trace: expected a non-empty string or null`,
    ],
    [
      "no stat",
      [...A, "measures", "stats"],
      [],
      `${P}.measures.stats: expected at least one measure`,
    ],
    [
      "two stats with one label",
      [...A, "measures", "stats", 1, "label"],
      "Net leverage",
      `${P}.measures.stats[1].label: expected a label no other measure has`,
    ],
    [
      "a stat value that is no string",
      [...A, "measures", "stats", 0, "value"],
      5.9,
      `${P}.measures.stats[0].value: expected a string or null`,
    ],
    [
      "a stat without its delta",
      [...A, "measures", "stats", 3, "delta"],
      null,
      `${P}.measures.stats[3].delta: expected a string`,
    ],
    [
      "no bullet row",
      [...A, "headroom", "rows"],
      [],
      `${P}.headroom.rows: expected at least one row`,
    ],
    [
      "two bullet rows with one label",
      [...A, "headroom", "rows", 1, "label"],
      "Net leverage",
      `${P}.headroom.rows[1].label: expected a label no other row has`,
    ],
    [
      "a bullet axis of zero",
      [...A, "headroom", "rows", 0, "axisMax"],
      0,
      `${P}.headroom.rows[0].axisMax: expected a number above zero`,
    ],
    [
      "a bullet value below zero",
      [...A, "headroom", "rows", 0, "value"],
      -1,
      `${P}.headroom.rows[0].value: expected a position from 0 to the axis max (8)`,
    ],
    [
      "a bullet value past the axis",
      [...A, "headroom", "rows", 0, "value"],
      9,
      `${P}.headroom.rows[0].value: expected a position from 0 to the axis max (8)`,
    ],
    [
      "a bullet target past the axis",
      [...A, "headroom", "rows", 0, "target"],
      9,
      `${P}.headroom.rows[0].target: expected a position from 0 to the axis max (8)`,
    ],
    [
      "a missing bullet value with a text",
      [...A, "headroom", "rows", 3, "text"],
      "7x",
      `${P}.headroom.rows[3].text: expected null beside a missing value`,
    ],
    [
      "a bullet value without a text",
      [...A, "headroom", "rows", 0, "text"],
      null,
      `${P}.headroom.rows[0].text: expected a text beside a present value`,
    ],
    [
      "a bullet row with a short table",
      [...A, "headroom", "rows", 0, "cells"],
      ["5.9x"],
      `${P}.headroom.rows[0].cells: expected 2 cells, one per column after the label`,
    ],
    [
      "a bullet cell that is empty",
      [...A, "headroom", "rows", 0, "cells", 0],
      "",
      `${P}.headroom.rows[0].cells[0]: expected a non-empty string or null`,
    ],
    [
      "no dumbbell row",
      [...A, "segments", "rows"],
      [],
      `${P}.segments.rows: expected at least one row`,
    ],
    [
      "two dumbbell rows with one label",
      [...A, "segments", "rows", 1, "label"],
      "Power and control",
      `${P}.segments.rows[1].label: expected a label no other row has`,
    ],
    [
      "an axis that does not rise",
      [...A, "segments", "axis"],
      { min: 60, max: 30 },
      `${P}.segments.axis: expected a max above the min`,
    ],
    [
      "a dumbbell end outside the axis",
      [...A, "segments", "rows", 0, "to"],
      61,
      `${P}.segments.rows[0].to: expected a position from 30 to 60`,
    ],
    [
      "a dumbbell row with both ends missing",
      [...A, "segments", "rows", 3, "to"],
      null,
      `${P}.segments.rows[3]: expected at least one end present`,
    ],
    [
      "two periods with one name",
      [...A, "segments", "names", 1],
      "FY24",
      `${P}.segments.names: expected two different names`,
    ],
    [
      "one period name",
      [...A, "segments", "names"],
      ["FY24"],
      `${P}.segments.names: expected 2 entries`,
    ],
    [
      "a dumbbell row with a short table",
      [...A, "segments", "rows", 0, "cells"],
      [],
      `${P}.segments.rows[0].cells: expected 2 cells, one per column after the label`,
    ],
    [
      "a contrary passage without its text",
      [...A, "contrary", "text"],
      null,
      `${P}.contrary.text: expected a string`,
    ],
    [
      "an unknown key in the watch passage",
      [...A, "watch", "level"],
      "x",
      `${P}.watch.level: unknown field`,
    ],
    [
      "an empty link address",
      [...A, "limitations", "href"],
      "",
      `${P}.limitations.href: expected a non-empty string`,
    ],
    [
      "no limitation",
      [...A, "limitations", "items"],
      [],
      `${P}.limitations.items: expected at least one limitation`,
    ],
    [
      "two limitations with one title",
      [...A, "limitations", "items", 1, "title"],
      "EBITDA is the company’s own measure",
      `${P}.limitations.items[1].title: expected a title no other limitation has`,
    ],
    [
      "two findings with one title",
      [...A, "findings", 1, "title"],
      "Deleveraging depends on keeping the cash",
      `${P}.findings[1].title: expected a name no other trace control on the page has`,
    ],
    [
      "a measure named like a finding",
      [...A, "measures", "stats", 0, "label"],
      "Earnings quality is high",
      `${P}.measures.stats[0].label: expected a name no other trace control on the page has`,
    ],
    [
      "a chart titled like a finding",
      [...A, "segments", "title"],
      "Earnings quality is high",
      `${P}.segments.title: expected a name no other trace control on the page has`,
    ],
    [
      "a limitation titled like the contrary passage",
      [...A, "limitations", "items", 0, "title"],
      "The cash may not stay",
      `${P}.limitations.items[0].title: expected a name no other trace control on the page has`,
    ],
    [
      "a watch passage titled like the contrary passage",
      [...A, "watch", "title"],
      "The cash may not stay",
      `${P}.watch.title: expected a name no other trace control on the page has`,
    ],
    [
      "an empty headroom table head",
      [...A, "headroom", "head"],
      [],
      `${P}.headroom.head: expected a heading for the label column`,
    ],
    [
      "an empty segments table head",
      [...A, "segments", "head"],
      [],
      `${P}.segments.head: expected a heading for the label column`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });

  it("refuses a run without its analysis page", () => {
    expect(readSlice(edited(A, undefined))).toEqual({
      kind: "invalid",
      reason: "runs[0].analysis: missing",
    });
  });
});

describe("the analysis page: the table side holds to the chart side", () => {
  const H = [...A, "headroom", "rows"] as const;
  const S = [...A, "segments", "rows"] as const;
  it.each<[string, readonly (string | number)[], unknown, string]>([
    [
      "a missing headroom value with a figure in the first cell",
      [...H, 3, "cells"],
      ["6.0x", "Covenant limit 7.25x"],
      `${P}.headroom.rows[3].cells[0]: expected null beside a missing value`,
    ],
    [
      "a drawn headroom value with n.a. in the first cell",
      [...H, 0, "cells"],
      [null, "Downgrade above 7.0x"],
      `${P}.headroom.rows[0].cells[0]: expected the value's text, not n.a.`,
    ],
    [
      "a headroom first cell that is not the start of the drawn text",
      [...H, 0, "cells"],
      ["6.9x", "Downgrade above 7.0x"],
      `${P}.headroom.rows[0].cells[0]: expected the value's text, which "5.9x of 7.0x" starts with`,
    ],
    [
      "a headroom first cell that is only the start of a word of the text",
      [...H, 0, "cells"],
      ["5.9", "Downgrade above 7.0x"],
      `${P}.headroom.rows[0].cells[0]: expected the value's text, which "5.9x of 7.0x" starts with`,
    ],
    [
      "no earlier mark and a figure in the earlier cell",
      [...S, 3, "cells"],
      ["40.0%", "44.0%"],
      `${P}.segments.rows[3].cells[0]: expected null beside a missing earlier mark`,
    ],
    [
      "an earlier mark and n.a. in the earlier cell",
      [...S, 0, "cells"],
      [null, "57.5%"],
      `${P}.segments.rows[0].cells[0]: expected the earlier text, not n.a.`,
    ],
    [
      "a later mark and n.a. in the later cell",
      [...S, 1, "cells"],
      ["51.9%", null],
      `${P}.segments.rows[1].cells[1]: expected the later text, not n.a.`,
    ],
    [
      "a segment text that is not its two cells",
      [...S, 0, "cells"],
      ["55.9%", "57.5%"],
      `${P}.segments.rows[0].text: expected the earlier and later cells joined by " to ", n.a. where missing`,
    ],
  ])("refuses %s", (_name, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});
