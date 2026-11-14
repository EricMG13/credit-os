import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const STM = ["runs", 0, "statements"] as const;
const P = "runs[0].statements";
const B = `${P}.bridges[0]`;

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
  });
  it.each([...bridgeCases])(
    "is invalid and names the failing path: %s",
    (_, steps, value, reason) => {
      expect(readSlice(edited(steps, value))).toEqual({ kind: "invalid", reason });
    },
  );
});
