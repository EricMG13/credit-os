import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./read";

type Json = Record<string, unknown>;
type Files = Json[];

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: Json };

/** A deep copy of the fixture's slice, and the evidence member of its first issuer's run `r`. */
const fresh = () => structuredClone(fixture.slice) as { issuers: { runs: Json[] }[] };
const evidenceOf = (slice: ReturnType<typeof fresh>, r = 0) =>
  (slice.issuers[0]?.runs[r] as Json)["evidence"] as Json & {
    sources: Json & { files: Files };
    summary: Json & { take: { download: Json } };
    moduleFilter: Json[];
    trace: Json & { rows: Json[] };
  };
const fileOf = (e: ReturnType<typeof evidenceOf>, i: number): Json => {
  const found = e.sources.files[i];
  if (found === undefined) throw new RangeError(`no file ${String(i)}`);
  return found;
};
const optionOf = (e: ReturnType<typeof evidenceOf>, i: number): Json => {
  const found = e.moduleFilter[i];
  if (found === undefined) throw new RangeError(`no option ${String(i)}`);
  return found;
};
const at = (r: number) => `issuers[0].runs[${String(r)}].evidence`;

function invalidReason(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

describe("readSlice, evidence", () => {
  it("reads the full run's evidence: the mock's text, with the file note the fixture words (a departure)", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const evidence = result.data.issuers[0]?.runs[0]?.evidence;
    expect(evidence?.intro).toBe("Where every figure and claim in this run comes from.");
    expect(evidence?.tabs).toEqual({ trace: "60", sources: "9", gaps: "7" });
    expect(evidence?.summary.delivered).toEqual({
      note: "Recovery was not assessable",
      progress: { text: "12 of 13", value: 12, max: 13 },
    });
    expect(evidence?.summary.counts.map((c) => [c.label, c.value, c.note])).toEqual([
      [
        "Source files",
        { kind: "value", text: "9", at: null },
        "7 read in full, 1 read in part, 1 unreadable",
      ],
      [
        "Calculations",
        { kind: "value", text: "148", at: null },
        "Each one traceable to its inputs",
      ],
      ["Gaps", { kind: "value", text: "7", at: null }, "2 high, 3 medium, 2 low"],
    ]);
    expect(evidence?.summary.run).toEqual({
      code: "HAE-20260930-FR-0003",
      hash: "9f2c41d07ab35e88c1e4f6a2b9d03c57e1a84f60b7d2c9153ea06f48d1b7c2a0",
    });
    const files = evidence?.sources.files ?? [];
    expect(files.map((f) => [f.name, f.state])).toEqual([
      ["annual-report-2026.pdf", "Read in full"],
      ["lender-presentation-nov-2026.pdf", "Read in full"],
      ["credit-agreement-2023.pdf", "Read in part"],
      ["q4-2026-kpi-pack.xlsx", "Read in full"],
      ["rating-report-oct-2026.pdf", "Unreadable"],
      ["sustainability-report-2026.pdf", "Read in full"],
      ["bond-prospectus-2028-notes.pdf", "Read in full"],
      ["peer-benchmark-extract.xlsx", "Read in full"],
      ["interim-results-q3-2026.pdf", "Read in full"],
    ]);
    expect(files[0]?.readers.shown.map((r) => [r.initials, r.name])).toEqual([
      ["BP", "Business profile"],
      ["FP", "Financial performance"],
      ["CS", "Capital structure"],
      ["CL", "Cash flow and liquidity"],
    ]);
    expect(files[0]?.readers.more).toMatchObject({ text: "+7", label: "7 more modules" });
    expect(evidence?.sources).toMatchObject({ visible: 5, moreLabel: "Show the other 4 files" });
  });

  it("reads a capped run and a first run that agree with what the run says elsewhere", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const runs = result.data.issuers[0]?.runs ?? [];
    for (const [index, gaps] of [
      [2, "3"],
      [3, "2"],
    ] as const) {
      const run = runs[index];
      expect(run?.evidence?.tabs.gaps).toBe(gaps);
      expect(run?.overview?.limitations.gapsLink.label).toBe(`See the ${gaps} gaps in Evidence`);
      expect(run?.evidence?.tabs.sources).toBe(String(run?.evidence?.sources.files.length));
    }
    expect(runs[2]?.evidence?.summary.delivered.progress.text).toBe("9 of 13");
    expect(runs[2]?.evidence?.summary.take.download.href).toBeNull();
    expect(runs[3]?.evidence?.sources.moreLabel).toBeNull();
  });

  it("keeps the loading run's evidence null, and rejects it on either side", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(result.data.issuers[0]?.runs[1]?.evidence).toBeNull();
    const loading = fresh();
    (loading.issuers[0]?.runs[1] as Json)["evidence"] = evidenceOf(loading, 0);
    expect(invalidReason(loading)).toContain(at(1));
    const loaded = fresh();
    (loaded.issuers[0]?.runs[0] as Json)["evidence"] = null;
    expect(invalidReason(loaded)).toContain(at(0));
  });

  const broken: [string, (e: ReturnType<typeof evidenceOf>) => unknown, string][] = [
    [
      "a file in an unknown state",
      (e) => (fileOf(e, 1)["state"] = "Skimmed"),
      "sources.files[1].state",
    ],
    [
      "a file name that is an empty string",
      (e) => (fileOf(e, 0)["name"] = ""),
      "sources.files[0].name",
    ],
    ["a hash that is an empty string", (e) => (fileOf(e, 2)["hash"] = ""), "sources.files[2].hash"],
    [
      "a file name given twice",
      (e) => (fileOf(e, 3)["name"] = "annual-report-2026.pdf"),
      "sources.files[3].name",
    ],
    [
      "a hash given twice",
      (e) => (fileOf(e, 4)["hash"] = fileOf(e, 0)["hash"]),
      "sources.files[4].hash",
    ],
    [
      "a shown reader that is not a module of the run",
      (e) => ((fileOf(e, 0)["readers"] as { shown: string[] }).shown[2] = "treasury"),
      "sources.files[0].readers.shown[2]",
    ],
    [
      "a reader behind the +N that is not a module of the run",
      (e) => ((fileOf(e, 0)["readers"] as { more: { ids: string[] } }).more.ids[1] = "treasury"),
      "sources.files[0].readers.more.ids[1]",
    ],
    [
      "a module that reads a file twice",
      (e) => ((fileOf(e, 0)["readers"] as { shown: string[] }).shown[1] = "business-profile"),
      "sources.files[0].readers.shown[1]",
    ],
    [
      "a +N that does not count its modules",
      (e) => ((fileOf(e, 0)["readers"] as { more: { text: string } }).more.text = "+6"),
      "sources.files[0].readers.more.text",
    ],
    [
      "a filter option that is not a module of the run",
      (e) => (optionOf(e, 2)["id"] = "treasury"),
      "moduleFilter[2].id",
    ],
    [
      "a filter option named otherwise than its module",
      (e) => (optionOf(e, 0)["name"] = "Profile"),
      "moduleFilter[0].name",
    ],
    [
      "a filter option listed twice",
      (e) => (e.moduleFilter[1] = optionOf(e, 0)),
      "moduleFilter[1].id",
    ],
    ["no files", (e) => (e.sources.files = []), "sources.files"],
    [
      "a hidden-files label when no file is hidden",
      (e) => (e.sources["visible"] = 9),
      "sources.moreLabel",
    ],
    [
      "a hidden-files label that names the wrong number of hidden files",
      (e) => (e.sources["moreLabel"] = "Show the other 3 files"),
      "sources.moreLabel",
    ],
    [
      "no hidden-files label when a file is hidden",
      (e) => (e.sources["moreLabel"] = null),
      "sources.moreLabel",
    ],
    ["no file visible", (e) => (e.sources["visible"] = 0), "sources.visible"],
    [
      "an unreadable file with no reason",
      (e) => (fileOf(e, 4)["why"] = null),
      "sources.files[4].why",
    ],
    [
      "a download with no address and no reason",
      (e) => (e.summary.take.download["href"] = null),
      "summary.take.download.reason",
    ],
    [
      "a download with an address and a reason",
      (e) => (e.summary.take.download["reason"] = "No."),
      "summary.take.download.reason",
    ],
    ["a tab count that is not text", (e) => ((e["tabs"] as Json)["gaps"] = 7), "tabs.gaps"],
    [
      "a run code that is an empty string",
      (e) => ((e.summary["run"] as Json)["code"] = ""),
      "summary.run.code",
    ],
  ];
  it.each(broken)("is invalid for %s, with its path", (_, edit, expected) => {
    const slice = fresh();
    edit(evidenceOf(slice));
    expect(invalidReason(slice)).toContain(`${at(0)}.${expected}`);
  });
});

const rowOf = (e: ReturnType<typeof evidenceOf>, id: string): Json => {
  const found = e.trace.rows.find((row) => row["id"] === id);
  if (found === undefined) throw new RangeError(`no trace row ${id}`);
  return found;
};

describe("readSlice, trace", () => {
  const read = () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    return result.data.issuers[0]?.runs ?? [];
  };

  it("reads the full run's trace: the mock's rows in the mock's order, with its heads and its tree", () => {
    const trace = read()[0]?.evidence?.trace;
    expect(trace?.title).toBe("Trace");
    expect(trace?.description).toBe(
      "One row per traced paragraph, row or figure. Open a row to see how it was derived.",
    );
    expect(trace?.columns).toEqual({
      id: "Item",
      item: "Statement",
      value: "Value",
      module: "Module",
      kind: "Kind",
      sources: "Sources",
    });
    const rows = trace?.rows ?? [];
    expect(rows).toHaveLength(60);
    const mock = ["T-0001", "T-0014", "T-0015", "T-0031", "T-0047", "T-0052", "T-0068"];
    expect(rows.map((r) => r.id).filter((id) => mock.includes(id))).toEqual(mock);
    expect(
      rows
        .filter((r) => mock.includes(r.id))
        .map((r) => [r.id, r.item, r.module, r.kind, r.sources]),
    ).toEqual([
      [
        "T-0001",
        "Stable credit with thin headroom: leverage is falling, but the 2028 notes need refinancing.",
        "Overview",
        "Passage",
        "6",
      ],
      ["T-0014", "Net leverage 4.6x", "Capital structure", "Figure", "3"],
      ["T-0015", "Interest cover 2.4x", "Capital structure", "Figure", "4"],
      [
        "T-0031",
        "Three customers bring 58% of revenue and one engine programme 34%.",
        "Business profile",
        "Passage",
        "2",
      ],
      ["T-0047", "Maturities by year", "Capital structure", "Chart", "5"],
      ["T-0052", "Receivables facility availability", "Capital structure", "Row", "1"],
      [
        "T-0068",
        "Management says no alternative part has passed certification.",
        "Business profile",
        "Passage",
        "0",
      ],
    ]);
    expect(rows.find((r) => r.id === "T-0001")?.moduleId).toBeNull();
    expect(rows.find((r) => r.id === "T-0068")?.note).toBe(
      "The module gave no source for this claim.",
    );
    const calc = rows.find((r) => r.id === "T-0014")?.calc;
    const lines = (node: typeof calc, depth = 0): string[] =>
      node === null || node === undefined
        ? []
        : [
            `${"  ".repeat(depth)}${node.label} | ${node.value ?? ""} | ${node.note ?? ""}`,
            ...node.children.flatMap((child) => lines(child, depth + 1)),
          ];
    expect(lines(calc)).toEqual([
      "Result | Net leverage | 4.6x · C-0412",
      "  Formula | Net debt ÷ EBITDA | 2,236 ÷ 486",
      "    Input | Net debt = gross debt − cash | 2,236 · C-0398",
      "      Source | Gross debt 2,398 | annual-report-2026.pdf · p. 112, note 18",
      "      Source | Cash 162 | annual-report-2026.pdf · p. 84",
      "    Input | EBITDA, company-adjusted | 486",
      "      Source | EBITDA 486 | lender-presentation-nov-2026.pdf · p. 9",
      "        Excerpt | “Adjusted EBITDA for the twelve months ended 30 September 2026 was USD 486 million (2025: USD 441 million).” | ",
    ]);
  });

  it("holds a row for every item a trace opens, in every loaded run, and says how many in its tab", () => {
    for (const run of read()) {
      if (run.evidence === null) continue;
      const held = run.evidence.trace.rows.map((r) => r.id);
      for (const trace of Object.values(run.traces)) expect(held).toContain(trace.evidenceItem);
      expect(run.evidence.tabs.trace).toBe(String(held.length));
    }
    expect(read().map((run) => run.evidence?.trace.rows.length)).toEqual([60, undefined, 0, 0]);
  });

  const brokenRows: [string, (e: ReturnType<typeof evidenceOf>) => unknown, string][] = [
    ["a row with no id", (e) => (rowOf(e, "T-0042")["id"] = ""), "trace.rows[11].id"],
    ["an id given twice", (e) => (rowOf(e, "T-0042")["id"] = "T-0001"), "trace.rows[11].id"],
    ["a statement that is not text", (e) => (rowOf(e, "T-0001")["item"] = 6), "trace.rows[0].item"],
    [
      "a module the run does not hold",
      (e) => (rowOf(e, "T-0014")["moduleId"] = "treasury"),
      "trace.rows[3].moduleId",
    ],
    [
      "a module named otherwise",
      (e) => (rowOf(e, "T-0014")["module"] = "Capital"),
      "trace.rows[3].module",
    ],
    [
      "an item with no module that is not on the Overview",
      (e) => (rowOf(e, "T-0001")["module"] = "Recovery"),
      "trace.rows[0].module",
    ],
    [
      "a value that is not a figure",
      (e) => (rowOf(e, "T-0014")["value"] = { kind: "sum" }),
      "trace.rows[3].value.kind",
    ],
    [
      "a count of sources that is not text",
      (e) => (rowOf(e, "T-0014")["sources"] = 3),
      "trace.rows[3].sources",
    ],
    [
      "a calculation that is not a tree",
      (e) => (rowOf(e, "T-0014")["calc"] = "4.6x"),
      "trace.rows[3].calc",
    ],
    [
      "a branch of the calculation with no children list",
      (e) => delete ((rowOf(e, "T-0014")["calc"] as Json)["children"] as Json[])[0]?.["children"],
      "trace.rows[3].calc.children[0].children",
    ],
    [
      "a note that is an empty string",
      (e) => (rowOf(e, "T-0068")["note"] = ""),
      "trace.rows[33].note",
    ],
    [
      "a head that is missing",
      (e) => delete (e.trace["columns"] as Json)["kind"],
      "trace.columns.kind",
    ],
    [
      "a tab count that is not the number of rows",
      (e) => ((e["tabs"] as Json)["trace"] = "59"),
      "tabs.trace",
    ],
  ];
  it.each(brokenRows)("is invalid for %s, with its path", (_, edit, expected) => {
    const slice = fresh();
    edit(evidenceOf(slice));
    expect(invalidReason(slice)).toContain(`${at(0)}.${expected}`);
  });

  it("is invalid for a trace that opens an item no row holds, with the trace's path", () => {
    const slice = fresh();
    const traces = (slice.issuers[0]?.runs[0] as Json)["traces"] as Record<string, Json>;
    (traces["net-leverage"] as Json)["evidenceItem"] = "T-9999";
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].traces.net-leverage.evidenceItem");
  });
});
