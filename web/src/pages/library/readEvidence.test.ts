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
  it("reads the full run's evidence as the mock words it", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const evidence = result.data.issuers[0]?.runs[0]?.evidence;
    expect(evidence?.intro).toBe("Where every figure and claim in this run comes from.");
    expect(evidence?.tabs).toEqual({ trace: "148", sources: "9", gaps: "7" });
    expect(evidence?.summary.delivered).toEqual({
      note: "Recovery was not assessable",
      progress: { text: "12 of 13", value: 12, max: 13 },
    });
    expect(evidence?.summary.counts.map((c) => [c.label, c.value, c.note])).toEqual([
      [
        "Source files",
        { kind: "value", text: "9", at: null },
        expect.stringContaining("1 read in part"),
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
