import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./read";

type Json = Record<string, unknown>;
type Evidence = Json & { jump: Json[] };

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: Json };

const fresh = () => structuredClone(fixture.slice) as { issuers: { runs: Json[] }[] };
const evidenceOf = (slice: ReturnType<typeof fresh>, r = 0) =>
  (slice.issuers[0]?.runs[r] as Json)["evidence"] as Evidence;
const targetOf = (e: Evidence, i: number): Json => (e.jump[i] as Json)["target"] as Json;
const at = "issuers[0].runs[0].evidence";

function reasonOf(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

describe("readSlice, the jump list", () => {
  it("reads four items in three groups: the mock's, but for one row id (Secured leverage names T-0104, the fixture's own row for that figure)", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const jump = result.data.issuers[0]?.runs[0]?.evidence?.jump;
    expect(jump?.map((j) => [j.group, j.label, j.detail, j.target])).toEqual([
      [
        "Figures",
        "Net leverage 4.6x",
        "Capital structure · T-0014",
        { tab: "trace", item: "T-0014" },
      ],
      [
        "Figures",
        "Secured leverage 3.3x",
        "Capital structure · T-0104",
        { tab: "trace", item: "T-0104" },
      ],
      ["Calculations", "Net debt ÷ EBITDA", "C-0412", { tab: "trace", item: "T-0014" }],
      [
        "Gaps",
        "Peer figures on the same basis",
        "Peer comparison · G-03",
        { tab: "gaps", item: "G-03" },
      ],
    ]);
  });

  it("gives each run that has evidence its own list, naming only rows that run holds", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const runs = result.data.issuers[0]?.runs ?? [];
    expect(runs.map((r) => r.evidence?.jump.map((j) => j.target.item))).toEqual([
      ["T-0014", "T-0104", "T-0014", "G-03"],
      undefined,
      ["G-01"],
      ["G-01"],
    ]);
  });

  const broken: [string, (e: Evidence) => void, string][] = [
    ["no jump list", (e) => delete (e as Json)["jump"], "jump"],
    [
      "a group the menu does not draw",
      (e) => ((e.jump[0] as Json)["group"] = "Sources"),
      "jump[0].group",
    ],
    ["a blank label", (e) => ((e.jump[2] as Json)["label"] = ""), "jump[2].label"],
    [
      "a tab the menu cannot open",
      (e) => (targetOf(e, 0)["tab"] = "sources"),
      "jump[0].target.tab",
    ],
    [
      "a trace item no row holds",
      (e) => (targetOf(e, 1)["item"] = "T-9999"),
      "jump[1].target.item",
    ],
    [
      "a gap the Gaps tab does not hold",
      (e) => (targetOf(e, 3)["item"] = "G-99"),
      "jump[3].target.item",
    ],
    [
      "a gap's id on the Trace tab when that tab lists no such row",
      (e) => {
        targetOf(e, 3)["tab"] = "trace";
        targetOf(e, 3)["item"] = "G-06";
      },
      "jump[3].target.item",
    ],
    [
      "a trace row's id on the Gaps tab",
      (e) => (targetOf(e, 0)["tab"] = "gaps"),
      "jump[0].target.item",
    ],
  ];
  it.each(broken)("is invalid for %s, with its path", (_, edit, expected) => {
    const slice = fresh();
    edit(evidenceOf(slice));
    expect(reasonOf(slice)).toContain(`${at}.${expected}`);
  });
});
