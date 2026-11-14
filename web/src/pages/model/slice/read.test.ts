import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const RUN = ["runs", 0] as const;

describe("readSlice", () => {
  it("is absent when the data file holds no model member", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });

  it("reads the fixture", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(result.data.runs[0]?.header.issuerName).toBe("TransDigm Group");
    expect(result.data.runs[0]?.limitations.items).toHaveLength(6);
    expect(result.data.runs[0]?.limitations.items[0]?.trace).toBe(
      "#/library/transdigm/2025-06-30/evidence",
    );
  });

  it("refuses a second run for the same issuer and run, naming the repeat", () => {
    const source = fixtureSlice() as { runs: unknown[] };
    source.runs.push(structuredClone(source.runs[0]));
    expect(readSlice(source)).toEqual({
      kind: "invalid",
      reason: "runs[1].run: expected a run no other run has",
    });
  });

  it("accepts a second run of the same issuer on another date", () => {
    const source = fixtureSlice() as { runs: { run: string }[] };
    const other = structuredClone(source.runs[0]) as { run: string };
    other.run = "2024-12-31";
    source.runs.push(other);
    expect(readSlice(source).kind).toBe("ok");
  });

  it("keeps a null trace as null", () => {
    const result = readSlice(edited([...RUN, "limitations", "items", 1, "trace"], null));
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(result.data.runs[0]?.limitations.items[1]?.trace).toBeNull();
  });

  it.each([
    ["not an object", edited([], 5), "slice: expected an object"],
    ["the slice with an extra key", edited(["extra"], 1), "extra: unknown field"],
    ["a run with an extra key", edited([...RUN, "extra"], 1), "runs[0].extra: unknown field"],
    ["a run list that is no list", edited(["runs"], {}), "runs: expected a list"],
    ["a run missing a key", edited([...RUN, "run"], undefined), "runs[0].run: missing"],
    [
      "a header flag that is no boolean",
      edited([...RUN, "header", "sample"], "yes"),
      "runs[0].header.sample: expected true or false",
    ],
    [
      "a header state the Run states set lacks",
      edited([...RUN, "header", "state"], "Done"),
      "runs[0].header.state: expected one of Queued, Running, Finished, Failed, Capped, Rejected, Interrupted",
    ],
    [
      "a link that is no string",
      edited([...RUN, "links", "report"], 3),
      "runs[0].links.report: expected a string",
    ],
    [
      "limitations with a null count",
      edited([...RUN, "limitations", "count"], null),
      "runs[0].limitations.count: expected a string",
    ],
    [
      "a limitation with a numeric trace",
      edited([...RUN, "limitations", "items", 2, "trace"], 4),
      "runs[0].limitations.items[2].trace: expected a string or null",
    ],
    [
      "a gap missing its reason",
      edited([...RUN, "limitations", "notEstablished", "items", 1, "reason"], undefined),
      "runs[0].limitations.notEstablished.items[1].reason: missing",
    ],
    [
      "a gap group with a numeric count",
      edited([...RUN, "limitations", "notEstablished", "count"], 3),
      "runs[0].limitations.notEstablished.count: expected a string",
    ],
    [
      "a bottom line with no trace",
      edited([...RUN, "front", "bottomLine", "trace"], undefined),
      "runs[0].front.bottomLine.trace: missing",
    ],
    [
      "a metric whose value is neither text nor withheld",
      edited([...RUN, "front", "headline", "metrics", 6, "value"], { text: 3 }),
      "runs[0].front.headline.metrics[6].value.text: expected a string or null",
    ],
    [
      "a withheld value that is not true",
      edited([...RUN, "front", "headline", "metrics", 7, "value", "withheld"], false),
      "runs[0].front.headline.metrics[7].value.withheld: expected true",
    ],
    [
      "a metric delta that is a number",
      edited([...RUN, "front", "headline", "metrics", 2, "delta"], 0.5),
      "runs[0].front.headline.metrics[2].delta: expected a string or null",
    ],
    [
      "a delta beside a missing value",
      edited([...RUN, "front", "headline", "metrics", 6, "delta"], "↗ 1.0x"),
      "runs[0].front.headline.metrics[6].delta: expected null beside a missing or withheld value",
    ],
    [
      "a delta beside a withheld value",
      edited([...RUN, "front", "headline", "metrics", 7, "delta"], "↗ $1m"),
      "runs[0].front.headline.metrics[7].delta: expected null beside a missing or withheld value",
    ],
    [
      "a fact with an unknown key",
      edited([...RUN, "front", "covers", "facts", 3, "extra"], 1),
      "runs[0].front.covers.facts[3].extra: unknown field",
    ],
    [
      "a part linking to a page that is not in the group",
      edited([...RUN, "front", "parts", 0, "to"], "forecast"),
      "runs[0].front.parts[0].to: expected one of analysis, statements, portfolio-fit or null",
    ],
  ])("is invalid and names the failing path: %s", (_, source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });
});

const STM = [...RUN, "statements"] as const;
const ROW = [...STM, "statements", 0, "rows", 0] as const;
const ROW_PATH = "runs[0].statements.statements[0].rows[0]";
const PAIR = { kind: "missing", reason: null } as const;

describe("readSlice: cases and statements", () => {
  it("reads two cases and four statements of seven columns", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    const run = result.data.runs[0];
    expect(run?.cases.map((c) => c.name)).toEqual(["Base case", "Downside case"]);
    expect(run?.statements.statements.map((s) => s.name)).toEqual([
      "Income statement",
      "Cash flow",
      "Balance sheet",
      "Key measures",
    ]);
    expect(run?.statements.columns.map((c) => c.period)).toEqual([
      "FY22",
      "FY23",
      "FY24",
      "LTM",
      "FY25E",
      "FY26E",
      "FY27E",
    ]);
  });

  it("reads a column delivered empty with a reason and rows without a cell for it", () => {
    const source = fixtureSlice() as { runs: { statements: Record<string, unknown> }[] };
    const statements = source.runs[0]?.statements;
    if (statements === undefined) throw new Error("no run");
    statements["columns"] = [
      { kind: "actual", period: "FY24", note: "Actual" },
      { kind: "empty", period: "Pro forma", note: null, reason: "none placed" },
      { kind: "forecast", period: "FY25E", notes: [{ text: "Base" }, { text: "Downside" }] },
    ];
    statements["statements"] = [
      {
        name: "Income statement",
        rows: [
          {
            label: "Revenue",
            kind: "plain",
            gap: false,
            trace: null,
            cells: [{ kind: "figure", text: "1", pos: 1 }, [PAIR, PAIR]],
          },
        ],
      },
    ];
    const result = readSlice(source);
    if (result.kind !== "ok") throw new Error(JSON.stringify(result));
    expect(result.data.runs[0]?.statements.columns[1]).toEqual({
      kind: "empty",
      period: "Pro forma",
      note: null,
      reason: "none placed",
    });
  });

  it.each([
    [
      "a case with a numeric name",
      edited([...RUN, "cases", 0, "name"], 3),
      "runs[0].cases[0].name: expected a string",
    ],
    [
      "a case missing its leaves-out text",
      edited([...RUN, "cases", 1, "leavesOut"], undefined),
      "runs[0].cases[1].leavesOut: missing",
    ],
    [
      "a case note that is a number",
      edited([...RUN, "cases", 0, "note"], 1),
      "runs[0].cases[0].note: expected a string or null",
    ],
    ["no case at all", edited([...RUN, "cases"], []), "runs[0].cases: expected at least one case"],
    [
      "no statement at all",
      edited([...STM, "statements"], []),
      "runs[0].statements.statements: expected at least one statement",
    ],
    [
      "two statements with one name",
      edited([...STM, "statements", 1, "name"], "Income statement"),
      "runs[0].statements.statements[1].name: expected a name no other statement has",
    ],
    [
      "a column of an unknown kind",
      edited([...STM, "columns", 0, "kind"], "quarter"),
      "runs[0].statements.columns[0].kind: expected one of actual, forecast, empty",
    ],
    [
      "a column with no kind",
      edited([...STM, "columns", 2, "kind"], undefined),
      "runs[0].statements.columns[2].kind: missing",
    ],
    [
      "an actual column whose note is null",
      edited([...STM, "columns", 0, "note"], null),
      "runs[0].statements.columns[0].note: expected a string",
    ],
    [
      "a forecast note that is a number",
      edited([...STM, "columns", 4, "notes", 1, "text"], 2),
      "runs[0].statements.columns[4].notes[1].text: expected a string",
    ],
    [
      "a forecast column with a note missing for one case",
      edited([...STM, "columns", 5, "notes"], [{ text: "Base" }]),
      "runs[0].statements.columns[5].notes: expected 2 notes, one per case",
    ],
    [
      "a row of an unknown kind",
      edited([...ROW, "kind"], "ratio"),
      `${ROW_PATH}.kind: expected one of plain, subtotal, total`,
    ],
    [
      "a row gap that is a number",
      edited([...ROW, "gap"], 1),
      `${ROW_PATH}.gap: expected true or false`,
    ],
    [
      "a row trace that is a number",
      edited([...ROW, "trace"], 1),
      `${ROW_PATH}.trace: expected a string or null`,
    ],
    [
      "a cell of an unknown kind",
      edited([...ROW, "cells", 0, "kind"], "zero"),
      `${ROW_PATH}.cells[0].kind: expected one of figure, missing, withheld`,
    ],
    [
      "a figure whose text is null",
      edited([...ROW, "cells", 1, "text"], null),
      `${ROW_PATH}.cells[1].text: expected a string`,
    ],
    [
      "a figure whose position is above 1",
      edited([...ROW, "cells", 1, "pos"], 1.2),
      `${ROW_PATH}.cells[1].pos: expected a number from -1 to 1`,
    ],
    [
      "a figure whose position is text",
      edited([...ROW, "cells", 1, "pos"], "0.5"),
      `${ROW_PATH}.cells[1].pos: expected a number from -1 to 1`,
    ],
    [
      "a missing cell with a numeric reason",
      edited([...STM, "statements", 1, "rows", 1, "cells", 1, "reason"], 5),
      "runs[0].statements.statements[1].rows[1].cells[1].reason: expected a string or null",
    ],
    [
      "a withheld cell that lost its reason key",
      edited([...STM, "statements", 1, "rows", 6, "cells", 4, 0, "reason"], undefined),
      "runs[0].statements.statements[1].rows[6].cells[4][0].reason: missing",
    ],
    [
      "an actual column given a list of cells",
      edited([...ROW, "cells", 0], [PAIR, PAIR]),
      `${ROW_PATH}.cells[0]: expected one cell for an actual column`,
    ],
    [
      "a forecast column given a single cell",
      edited([...ROW, "cells", 4], PAIR),
      `${ROW_PATH}.cells[4]: expected a list of 2 cells, one per case`,
    ],
    [
      "a forecast column with one case's cell missing",
      edited([...ROW, "cells", 6], [PAIR]),
      `${ROW_PATH}.cells[6]: expected a list of 2 cells, one per case`,
    ],
    [
      "a row with a cell too few",
      edited([...ROW, "cells"], [PAIR]),
      `${ROW_PATH}.cells: expected 7 entries, one per column that is not empty`,
    ],
  ])("is invalid and names the failing path: %s", (_, source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });
});

const TRACE_REPEAT = "expected a name no other trace control on the page has";

describe("readSlice: no two trace controls on a page share a name (front, limitations, statements)", () => {
  it.each([
    [
      "a fact labelled as an earlier fact",
      edited([...RUN, "front", "covers", "facts", 1, "label"], "Currency and units"),
      "runs[0].front.covers.facts[1].label",
    ],
    [
      "a metric labelled as an earlier metric",
      edited([...RUN, "front", "headline", "metrics", 1, "label"], "Revenue"),
      "runs[0].front.headline.metrics[1].label",
    ],
    [
      "a part titled as an earlier part",
      edited([...RUN, "front", "parts", 1, "title"], "Analysis"),
      "runs[0].front.parts[1].title",
    ],
    [
      "a fact labelled as a metric",
      edited([...RUN, "front", "covers", "facts", 0, "label"], "Net leverage"),
      "runs[0].front.covers.facts[0].label",
    ],
    [
      "a part titled as a fact",
      edited([...RUN, "front", "parts", 0, "title"], "Cases"),
      "runs[0].front.parts[0].title",
    ],
    [
      "a metric labelled as the bottom line's own control",
      edited([...RUN, "front", "headline", "metrics", 0, "label"], "the bottom line"),
      "runs[0].front.headline.metrics[0].label",
    ],
    [
      "a limitation titled as an earlier limitation",
      edited([...RUN, "limitations", "items", 1, "title"], "EBITDA is the company’s own measure"),
      "runs[0].limitations.items[1].title",
    ],
    [
      "a statement row labelled as an earlier row of its statement",
      edited([...STM, "statements", 0, "rows", 1, "label"], "Revenue"),
      "runs[0].statements.statements[0].rows[1].label",
    ],
    [
      "a statement row labelled as a case",
      edited([...ROW, "label"], "Base case"),
      `${ROW_PATH}.label`,
    ],
    [
      "a statement row labelled as a chart title",
      edited([...ROW, "label"], "Debt by instrument"),
      `${ROW_PATH}.label`,
    ],
    [
      "a debt chart titled as the recovery chart",
      edited([...STM, "debt", "stack", "title"], "Recovery by class and case"),
      "runs[0].statements.recovery.title",
    ],
    [
      "the comparison titled as a bridge",
      edited([...STM, "comparison", "title"], "Net debt walk"),
      "runs[0].statements.comparison.title",
    ],
    [
      "a bridge titled as a case",
      edited([...STM, "bridges", 0, "title"], "Downside case"),
      "runs[0].statements.bridges[0].title",
    ],
  ])("refuses %s, naming the second one", (_, source, where) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason: `${where}: ${TRACE_REPEAT}` });
  });

  it("accepts a repeated name where one of the two draws no control", () => {
    const source = edited([...RUN, "front", "headline", "metrics", 1, "label"], "Revenue");
    const run = (source as { runs: { front: { headline: { metrics: { trace: unknown }[] } } }[] })
      .runs[0];
    if (run === undefined) throw new Error("no run");
    const metric = run.front.headline.metrics[1];
    if (metric === undefined) throw new Error("no metric");
    metric.trace = null;
    expect(readSlice(source).kind).toBe("ok");
  });

  it("accepts a statement row label that another statement repeats (one statement is open at a time)", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    const [income, cash] = result.data.runs[0]?.statements.statements ?? [];
    expect(income?.rows[2]?.label).toBe("EBITDA as defined");
    expect(cash?.rows[0]?.label).toBe("EBITDA as defined");
  });
});

describe("readSlice: lists the pages draw hold something", () => {
  it.each([
    [
      "no headline metric",
      edited([...RUN, "front", "headline", "metrics"], []),
      "runs[0].front.headline.metrics: expected at least one metric",
    ],
    [
      "no fact",
      edited([...RUN, "front", "covers", "facts"], []),
      "runs[0].front.covers.facts: expected at least one fact",
    ],
    [
      "no part",
      edited([...RUN, "front", "parts"], []),
      "runs[0].front.parts: expected at least one part",
    ],
    [
      "no limitation",
      edited([...RUN, "limitations", "items"], []),
      "runs[0].limitations.items: expected at least one limitation",
    ],
    [
      "a statement with no row (its empty column's reason would not be drawn)",
      edited([...STM, "statements", 1, "rows"], []),
      "runs[0].statements.statements[1].rows: expected at least one row",
    ],
    [
      "no column",
      edited([...STM, "columns"], []),
      "runs[0].statements.columns: expected at least one column",
    ],
  ])("refuses %s", (_, source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });

  it("reads a run with nothing yet to report as not established, which the page draws as its heading and count", () => {
    const result = readSlice(edited([...RUN, "limitations", "notEstablished", "items"], []));
    expect(result.kind).toBe("ok");
  });
});

describe("readSlice: a string the page draws is never empty", () => {
  const P = "runs[0]";
  const NON_EMPTY = "expected a non-empty string";
  const NON_EMPTY_OR_NULL = "expected a non-empty string or null";
  it.each([
    [["issuer"], `${P}.issuer`],
    [["run"], `${P}.run`],
    [["header", "issuerName"], `${P}.header.issuerName`],
    [["header", "asOf"], `${P}.header.asOf`],
    [["header", "purpose"], `${P}.header.purpose`],
    [["limitations", "count"], `${P}.limitations.count`],
    [["limitations", "gapsLinkText"], `${P}.limitations.gapsLinkText`],
    [["limitations", "lead"], `${P}.limitations.lead`],
    [["limitations", "items", 0, "title"], `${P}.limitations.items[0].title`],
    [["limitations", "items", 0, "label"], `${P}.limitations.items[0].label`],
    [["limitations", "items", 0, "text"], `${P}.limitations.items[0].text`],
    [["limitations", "notEstablished", "count"], `${P}.limitations.notEstablished.count`],
    [
      ["limitations", "notEstablished", "items", 0, "title"],
      `${P}.limitations.notEstablished.items[0].title`,
    ],
    [
      ["limitations", "notEstablished", "items", 0, "reason"],
      `${P}.limitations.notEstablished.items[0].reason`,
    ],
    [["front", "bottomLine", "lead"], `${P}.front.bottomLine.lead`],
    [["front", "bottomLine", "rest"], `${P}.front.bottomLine.rest`],
    [["front", "headline", "period"], `${P}.front.headline.period`],
    [["front", "headline", "metrics", 0, "label"], `${P}.front.headline.metrics[0].label`],
    [
      ["front", "headline", "metrics", 0, "definition"],
      `${P}.front.headline.metrics[0].definition`,
    ],
    [["front", "covers", "facts", 0, "label"], `${P}.front.covers.facts[0].label`],
    [["front", "covers", "facts", 0, "value"], `${P}.front.covers.facts[0].value`],
    [["front", "parts", 0, "title"], `${P}.front.parts[0].title`],
    [["front", "parts", 0, "text"], `${P}.front.parts[0].text`],
    [["cases", 0, "name"], `${P}.cases[0].name`],
    [["cases", 0, "tag"], `${P}.cases[0].tag`],
    [["cases", 0, "assumption"], `${P}.cases[0].assumption`],
    [["cases", 0, "leavesOut"], `${P}.cases[0].leavesOut`],
    [["statements", "intro"], `${P}.statements.intro`],
    [["statements", "columns", 0, "period"], `${P}.statements.columns[0].period`],
    [["statements", "columns", 0, "note"], `${P}.statements.columns[0].note`],
    [["statements", "columns", 4, "notes", 0, "text"], `${P}.statements.columns[4].notes[0].text`],
    [["statements", "statements", 0, "name"], `${P}.statements.statements[0].name`],
    [
      ["statements", "statements", 0, "rows", 0, "label"],
      `${P}.statements.statements[0].rows[0].label`,
    ],
    [
      ["statements", "statements", 0, "rows", 0, "cells", 0, "text"],
      `${P}.statements.statements[0].rows[0].cells[0].text`,
    ],
    [["statements", "recovery", "title"], `${P}.statements.recovery.title`],
    [["statements", "recovery", "head"], `${P}.statements.recovery.head`],
    [["statements", "debt", "stack", "head", 0], `${P}.statements.debt.stack.head[0]`],
    [["statements", "bridges", 0, "head", 0], `${P}.statements.bridges[0].head[0]`],
    [["statements", "bridges", 0, "rows", 0, "label"], `${P}.statements.bridges[0].rows[0].label`],
    [["statements", "comparison", "tableHead"], `${P}.statements.comparison.tableHead`],
    [["statements", "comparison", "rowLabels", 0], `${P}.statements.comparison.rowLabels[0]`],
    [["statements", "gap", "title"], `${P}.statements.gap.title`],
    [["statements", "gap", "reason"], `${P}.statements.gap.reason`],
    [["statements", "checkFigure", "title"], `${P}.statements.checkFigure.title`],
    [["statements", "checkFigure", "text"], `${P}.statements.checkFigure.text`],
  ] as [(string | number)[], string][])("refuses an empty string at %j", (steps, where) => {
    expect(readSlice(edited([...RUN, ...steps], ""))).toEqual({
      kind: "invalid",
      reason: `${where}: ${NON_EMPTY}`,
    });
  });

  it.each([
    [["front", "headline", "metrics", 0, "note"], `${P}.front.headline.metrics[0].note`],
    [["cases", 0, "note"], `${P}.cases[0].note`],
    [
      ["statements", "statements", 1, "rows", 1, "cells", 1, "reason"],
      `${P}.statements.statements[1].rows[1].cells[1].reason`,
    ],
  ] as [(string | number)[], string][])(
    "refuses an empty string, not null, at %j",
    (steps, where) => {
      expect(readSlice(edited([...RUN, ...steps], ""))).toEqual({
        kind: "invalid",
        reason: `${where}: ${NON_EMPTY_OR_NULL}`,
      });
    },
  );
});

describe("readSlice: a string of spaces is as empty as no string", () => {
  const P = "runs[0]";
  it.each([
    [["header", "issuerName"], `${P}.header.issuerName`, "expected a non-empty string"],
    [
      ["front", "headline", "metrics", 0, "label"],
      `${P}.front.headline.metrics[0].label`,
      "expected a non-empty string",
    ],
    [
      ["statements", "statements", 0, "name"],
      `${P}.statements.statements[0].name`,
      "expected a non-empty string",
    ],
    [
      ["front", "headline", "metrics", 0, "note"],
      `${P}.front.headline.metrics[0].note`,
      "expected a non-empty string or null",
    ],
  ] as [(string | number)[], string, string][])('refuses " " at %j', (steps, where, what) => {
    expect(readSlice(edited([...RUN, ...steps], " \t "))).toEqual({
      kind: "invalid",
      reason: `${where}: ${what}`,
    });
  });
});

describe("readSlice: an address into the library starts with #/", () => {
  const P = "runs[0]";
  const OFF = 'expected an address starting with "#/"';
  it.each([
    [["front", "bottomLine", "trace"], `${P}.front.bottomLine.trace`, "https://example.invalid/x"],
    [["links", "report"], `${P}.links.report`, "https://example.invalid/x"],
    [["links", "evidence"], `${P}.links.evidence`, "//example.invalid/x"],
    [["links", "library"], `${P}.links.library`, "library/transdigm"],
    [["links", "evidenceGaps"], `${P}.links.evidenceGaps`, "/#/x"],
    [["cases", 0, "trace"], `${P}.cases[0].trace`, "http://example.invalid/x"],
    [
      ["statements", "statements", 0, "rows", 0, "trace"],
      `${P}.statements.statements[0].rows[0].trace`,
      "https://example.invalid/x",
    ],
    [
      ["limitations", "items", 0, "trace"],
      `${P}.limitations.items[0].trace`,
      "ftp://example.invalid",
    ],
  ] as [(string | number)[], string, string][])("refuses %j holding %s", (steps, where, value) => {
    expect(readSlice(edited([...RUN, ...steps], value))).toEqual({
      kind: "invalid",
      reason: `${where}: ${OFF}`,
    });
  });

  it("leaves the published model's address and the check figure's to their own rule", () => {
    expect(
      readSlice(edited([...RUN, "statements", "checkFigure", "href"], "https://example.invalid/f"))
        .kind,
    ).toBe("ok");
  });
});
