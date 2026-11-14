import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const STM = ["runs", 0, "statements"] as const;
const P = "runs[0].statements";
const B = `${P}.bridges[0]`;
const C = `${P}.comparison`;
const S = `${P}.debt.stack`;
const M = `${P}.debt.maturities`;
const R = `${P}.recovery`;

type Case = [string, readonly (string | number)[], unknown, string];

const bridgeCases: Case[] = [
  ["no bridge", [...STM, "bridges"], [], `${P}.bridges: expected at least one bridge`],
  [
    "two bridges with one title",
    [...STM, "bridges", 1, "title"],
    "EBITDA bridge",
    `${P}.bridges[1].title: expected a title no other bridge has`,
  ],
  [
    "one tick",
    [...STM, "bridges", 0, "yTicks"],
    [{ value: 0, label: "0" }],
    `${B}.yTicks: expected at least two ticks`,
  ],
  [
    "a first tick above zero",
    [...STM, "bridges", 0, "yTicks", 0, "value"],
    10,
    `${B}.yTicks[0].value: expected the first tick to be 0`,
  ],
  [
    "ticks that do not rise",
    [...STM, "bridges", 0, "yTicks", 2, "value"],
    1500,
    `${B}.yTicks[2].value: expected ticks in rising order`,
  ],
  [
    "a tick without a label",
    [...STM, "bridges", 0, "yTicks", 1, "label"],
    "",
    `${B}.yTicks[1].label: expected a non-empty string`,
  ],
  [
    "steps for one case only",
    [...STM, "bridges", 0, "caseSteps"],
    [[{ label: "FY24", kind: "missing" }]],
    `${B}.caseSteps: expected 2 lists of steps, one per case`,
  ],
  [
    "no step in a case",
    [...STM, "bridges", 0, "caseSteps", 1],
    [],
    `${B}.caseSteps[1]: expected at least one step`,
  ],
  [
    "two steps with one label",
    [...STM, "bridges", 0, "caseSteps", 0, 1, "label"],
    "FY24",
    `${B}.caseSteps[0][1].label: expected a label no other step has`,
  ],
  [
    "a negative position",
    [...STM, "bridges", 0, "caseSteps", 0, 1, "from"],
    -1,
    `${B}.caseSteps[0][1].from: expected a number of zero or more`,
  ],
  [
    "a position past the last tick",
    [...STM, "bridges", 0, "caseSteps", 0, 0, "to"],
    7000,
    `${B}.caseSteps[0][0].to: expected a position within the axis (at most 6000)`,
  ],
  [
    "a total that starts above the baseline",
    [...STM, "bridges", 0, "caseSteps", 0, 0, "from"],
    10,
    `${B}.caseSteps[0][0].from: expected 0 for a total`,
  ],
  [
    "an increase that falls",
    [...STM, "bridges", 0, "caseSteps", 0, 1, "to"],
    100,
    `${B}.caseSteps[0][1].to: expected a position at or above from for an increase`,
  ],
  [
    "a decrease that rises",
    [...STM, "bridges", 0, "caseSteps", 0, 4, "to"],
    5000,
    `${B}.caseSteps[0][4].to: expected a position at or below from for a decrease`,
  ],
  [
    "a step without text",
    [...STM, "bridges", 0, "caseSteps", 0, 1, "text"],
    "",
    `${B}.caseSteps[0][1].text: expected a non-empty string`,
  ],
  [
    "a missing step that carries text",
    [...STM, "bridges", 0, "caseSteps", 0, 1],
    { label: "Volume", kind: "missing", text: "+1" },
    `${B}.caseSteps[0][1].text: unknown field`,
  ],
  [
    "a table heading that is not the case names",
    [...STM, "bridges", 0, "head", 1],
    "Base",
    `${B}.head: expected the case names after the first heading, in order`,
  ],
  [
    "two table rows with one label",
    [...STM, "bridges", 0, "rows", 2, "label"],
    "Volume",
    `${B}.rows[2].label: expected a label no other row has`,
  ],
  [
    "a row short of the steps",
    [...STM, "bridges", 0, "rows"],
    [{ label: "Volume", cells: ["330", "150"], trace: null }],
    `${B}.rows: expected 6 rows, one per step`,
  ],
  [
    "a second case with a step fewer than the table's rows",
    [...STM, "bridges", 0, "caseSteps", 1],
    [
      { label: "FY24", kind: "total", from: 0, to: 4173, text: "4,173" },
      { label: "Volume", kind: "up", from: 4173, to: 4323, text: "+150" },
      { label: "Price", kind: "up", from: 4323, to: 4503, text: "+180" },
      { label: "Acquisitions", kind: "up", from: 4503, to: 4623, text: "+120" },
      { label: "Costs", kind: "down", from: 4623, to: 4560, text: "-63" },
    ],
    `${B}.caseSteps[1]: expected 6 steps, one per row`,
  ],
  [
    "a second case with a step more than the table's rows",
    [...STM, "bridges", 0, "caseSteps", 1],
    [
      { label: "FY24", kind: "total", from: 0, to: 4173, text: "4,173" },
      { label: "Volume", kind: "up", from: 4173, to: 4323, text: "+150" },
      { label: "Price", kind: "up", from: 4323, to: 4503, text: "+180" },
      { label: "Acquisitions", kind: "up", from: 4503, to: 4623, text: "+120" },
      { label: "Costs", kind: "down", from: 4623, to: 4560, text: "-63" },
      { label: "FY25E", kind: "total", from: 0, to: 4560, text: "4,560" },
      { label: "Extra", kind: "total", from: 0, to: 4560, text: "4,560" },
    ],
    `${B}.caseSteps[1]: expected 6 steps, one per row`,
  ],
  [
    "an empty bridge trace",
    [...STM, "bridges", 0, "trace"],
    "",
    `${B}.trace: expected a non-empty string or null`,
  ],
  [
    "an empty published address",
    [...STM, "published"],
    { kind: "html", href: "" },
    `${P}.published.href: expected a non-empty string`,
  ],
  [
    "an empty figure check address",
    [...STM, "checkFigure", "href"],
    "",
    `${P}.checkFigure.href: expected a non-empty string`,
  ],
  [
    "an empty run link",
    ["runs", 0, "links", "evidence"],
    "",
    "runs[0].links.evidence: expected a non-empty string",
  ],
  [
    "an empty statement row trace",
    [...STM, "statements", 0, "rows", 0, "trace"],
    "",
    `${P}.statements[0].rows[0].trace: expected a non-empty string or null`,
  ],
  [
    "a panel without a table label",
    [...STM, "comparison", "panels", 0, "tableLabel"],
    "",
    `${C}.panels[0].tableLabel: expected a non-empty string`,
  ],
  [
    "two panels with one table label",
    [...STM, "comparison", "panels", 1, "tableLabel"],
    "Revenue, USD millions",
    `${C}.panels[1].tableLabel: expected a label no other panel has`,
  ],
  [
    "a row with one cell",
    [...STM, "bridges", 0, "rows", 1, "cells"],
    ["330"],
    `${B}.rows[1].cells: expected 2 cells, one per case`,
  ],
  [
    "an empty cell string",
    [...STM, "bridges", 0, "rows", 1, "cells", 0],
    "",
    `${B}.rows[1].cells[0]: expected a non-empty string or null`,
  ],
  [
    "a figure beside a missing step",
    [...STM, "bridges", 1, "rows", 4, "cells", 0],
    "5",
    `${P}.bridges[1].rows[4].cells[0]: expected null exactly where the step is missing`,
  ],
  [
    "n.a. beside a present step",
    [...STM, "bridges", 0, "rows", 1, "cells", 0],
    null,
    `${B}.rows[1].cells[0]: expected null exactly where the step is missing`,
  ],
];

const comparisonCases: Case[] = [
  ["no panel", [...STM, "comparison", "panels"], [], `${C}.panels: expected at least one panel`],
  [
    "two panels with one measure",
    [...STM, "comparison", "panels", 1, "measure"],
    "Revenue, USD millions",
    `${C}.panels[1].measure: expected a measure no other panel has`,
  ],
  [
    "a panel max of zero",
    [...STM, "comparison", "panels", 0, "max"],
    0,
    `${C}.panels[0].max: expected a number above zero`,
  ],
  [
    "a negative value",
    [...STM, "comparison", "panels", 0, "values", 0],
    -5,
    `${C}.panels[0].values[0]: expected a number of zero or more`,
  ],
  [
    "a value above the panel max",
    [...STM, "comparison", "panels", 0, "values", 0],
    20000,
    `${C}.panels[0].values[0]: expected a number of at most the panel's max`,
  ],
  [
    "a present value without text",
    [...STM, "comparison", "panels", 0, "texts", 0],
    null,
    `${C}.panels[0].texts[0]: expected a text beside a present value`,
  ],
  [
    "text beside a missing value",
    [...STM, "comparison", "panels", 0, "values", 0],
    null,
    `${C}.panels[0].texts[0]: expected null beside a missing value`,
  ],
  [
    "an empty text",
    [...STM, "comparison", "panels", 0, "texts", 0],
    "",
    `${C}.panels[0].texts[0]: expected a non-empty string or null`,
  ],
  [
    "one row label",
    [...STM, "comparison", "rowLabels"],
    ["Base"],
    `${C}.rowLabels: expected 2 entries`,
  ],
  [
    "two row labels alike",
    [...STM, "comparison", "rowLabels"],
    ["Base", "Base"],
    `${C}.rowLabels[1]: expected a label the other row does not have`,
  ],
  [
    "two cases with one name",
    ["runs", 0, "cases", 1, "name"],
    "Base case",
    "runs[0].cases[1].name: expected a name the other case does not have",
  ],
  [
    "three cases",
    ["runs", 0, "cases", 2],
    { ...(fixtureCase() as object), name: "Third case" },
    "runs[0].cases: expected two cases, the side by side chart draws two",
  ],
];

function fixtureCase(): unknown {
  return (fixtureSlice() as { runs: { cases: unknown[] }[] }).runs[0]?.cases[0];
}

const stackCases: Case[] = [
  ["no part", [...STM, "debt", "stack", "parts"], [], `${S}.parts: expected at least one part`],
  [
    "two parts with one name",
    [...STM, "debt", "stack", "parts", 1, "name"],
    "Term loans",
    `${S}.parts[1].name: expected a name no other part has`,
  ],
  [
    "a segment of zero",
    [...STM, "debt", "stack", "parts", 0, "value"],
    0,
    `${S}.parts[0].value: expected a number above zero`,
  ],
  [
    "a part without an amount",
    [...STM, "debt", "stack", "parts", 0, "text"],
    "",
    `${S}.parts[0].text: expected a non-empty string`,
  ],
  [
    "a part without a share",
    [...STM, "debt", "stack", "parts", 0, "share"],
    "",
    `${S}.parts[0].share: expected a non-empty string`,
  ],
  [
    "two table headings",
    [...STM, "debt", "stack", "head"],
    ["Instrument", "USD millions"],
    `${S}.head: expected 3 entries, the label, amount and share headings`,
  ],
];

/** The rules both bar charts share, run for maturities and for recovery. */
function columnsCases(
  key: readonly string[],
  at: string,
  last: number,
  firstGroup: string,
  firstSeries: string,
): Case[] {
  const K = [...STM, ...key] as const;
  return [
    ["no group", [...K, "groups"], [], `${at}.groups: expected at least one group`],
    [
      "two groups with one label",
      [...K, "groups", 1, "label"],
      firstGroup,
      `${at}.groups[1].label: expected a label no other group has`,
    ],
    ["no series", [...K, "series"], [], `${at}.series: expected at least one series`],
    [
      "two series with one name",
      [...K, "series", 1, "name"],
      firstSeries,
      `${at}.series[1].name: expected a name no other series has`,
    ],
    [
      "values short of the groups",
      [...K, "series", 0, "values"],
      [1],
      `${at}.series[0].values: expected ${String(key[0] === "recovery" ? 3 : 6)} entries, one per group`,
    ],
    [
      "labels short of the groups",
      [...K, "series", 0, "labels"],
      ["1"],
      `${at}.series[0].labels: expected ${String(key[0] === "recovery" ? 3 : 6)} entries, one per group`,
    ],
    [
      "a present value without a label",
      [...K, "series", 0, "labels", 1],
      null,
      `${at}.series[0].labels[1]: expected a label beside a present value`,
    ],
    [
      "a label beside a missing value",
      [...K, "series", 1, "values", 1],
      null,
      `${at}.series[1].labels[1]: expected null beside a missing value`,
    ],
    [
      "a negative value",
      [...K, "series", 0, "values", 1],
      -1,
      `${at}.series[0].values[1]: expected a number of zero or more`,
    ],
    [
      "a value past the last tick",
      [...K, "series", 0, "values", 1],
      last + 1,
      `${at}.series[0].values[1]: expected a position within the axis (at most ${String(last)})`,
    ],
    [
      "an empty label",
      [...K, "series", 0, "labels", 1],
      "",
      `${at}.series[0].labels[1]: expected a non-empty string or null`,
    ],
    [
      "ticks that do not rise",
      [...K, "yTicks", 1, "value"],
      0,
      `${at}.yTicks[1].value: expected ticks in rising order`,
    ],
    [
      "a first tick above zero",
      [...K, "yTicks", 0, "value"],
      1,
      `${at}.yTicks[0].value: expected the first tick to be 0`,
    ],
  ];
}

const pageCases: Case[] = [
  [
    "a published model of another kind",
    [...STM, "published"],
    { kind: "pdf", href: "x.pdf" },
    `${P}.published.kind: expected one of markdown, html`,
  ],
  [
    "a published model without an address",
    [...STM, "published"],
    { kind: "html" },
    `${P}.published.href: missing`,
  ],
  [
    "a published model that is neither null nor a record of kind and href",
    [...STM, "published"],
    { wrong: true },
    `${P}.published: expected null or an object with kind and href`,
  ],
  [
    "a gap title that is a number",
    [...STM, "gap", "title"],
    1,
    `${P}.gap.title: expected a string`,
  ],
  [
    "a figure check without an address",
    [...STM, "checkFigure", "href"],
    undefined,
    `${P}.checkFigure.href: missing`,
  ],
];

describe("readSlice: the second half of the Model page", () => {
  it("reads the bridges, the comparison, the debt, the recovery and the links", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(`${result.kind}: ${JSON.stringify(result)}`);
    const page = result.data.runs[0]?.statements;
    expect(page?.bridges.map((b) => b.title)).toEqual(["EBITDA bridge", "Net debt walk"]);
    expect(page?.bridges.map((b) => b.caseSteps.map((s) => s.length))).toEqual([
      [6, 6],
      [6, 6],
    ]);
    expect(page?.comparison.panels.map((p) => p.texts)).toContainEqual(["2,790", null]);
    expect(page?.debt.stack.parts.map((p) => p.share)).toEqual(["38%", "35%", "25%", "2%"]);
    expect(page?.debt.maturities.series[0]?.values).toEqual([null, 0, 3600, 0, 4500, 3200]);
    expect(page?.recovery.series[1]?.labels).toEqual(["100%", "31%", null]);
    expect(page?.published).toBeNull();
  });

  it.each([[{ kind: "markdown", href: "model.md" }], [{ kind: "html", href: "model.html" }]])(
    "reads a published model %j",
    (published) => {
      const result = readSlice(edited([...STM, "published"], published));
      if (result.kind !== "ok") throw new Error(result.kind);
      expect(result.data.runs[0]?.statements.published).toEqual(published);
    },
  );

  it.each([
    ...bridgeCases,
    ...comparisonCases,
    ...stackCases,
    ...columnsCases(["debt", "maturities"], M, 5000, "2026", "Term loans"),
    ...columnsCases(["recovery"], R, 100, "Term loans and secured notes", "Base case"),
    ...pageCases,
  ])("is invalid and names the failing path: %s", (_, steps, value, reason) => {
    expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
  });
});
