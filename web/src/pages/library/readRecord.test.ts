import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./read";

type Json = Record<string, unknown>;
type Rows = Json[];
type Evidence = Json & {
  record: Json & {
    timings: Json & { rows: Rows };
    hashes: Json & { items: Rows };
    spend: Json & { progress: Json };
    calls: Json & { rows: Rows; total: Json };
    registers: Json & { rows: Rows; downloadAll: Json };
  };
};

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: Json };

const fresh = () => structuredClone(fixture.slice) as { issuers: { runs: Json[] }[] };
const evidenceOf = (slice: ReturnType<typeof fresh>, r = 0) =>
  (slice.issuers[0]?.runs[r] as Json)["evidence"] as Evidence;
const at = "issuers[0].runs[0].evidence";
const cellAt = (rows: Rows, i: number, key: string): Json => (rows[i] as Json)[key] as Json;

function reasonOf(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

function read() {
  const result = readSlice(fixture.slice);
  if (result.kind !== "ok") throw new Error(result.kind);
  const runs = result.data.issuers[0]?.runs ?? [];
  return runs.map((run) => run.evidence);
}

describe("readSlice, Evidence Record", () => {
  it("reads the mock's module timings, with n.a. for a module that has no time", () => {
    const record = read()[0]?.record;
    expect(record?.timings.columns).toEqual([
      "Module",
      "State",
      "Started, min",
      "Accepted, min",
      "Took, min",
    ]);
    const text = (c: unknown) => (c === null ? null : (c as { text: string }).text);
    expect(
      record?.timings.rows.map((r) => [
        r.module,
        r.state,
        text(r.started),
        text(r.accepted),
        text(r.took),
      ]),
    ).toEqual([
      ["Business profile", "Delivered", "0.0", "6.0", "6.0"],
      ["Financial performance", "Delivered", "1.6", "9.6", "8.0"],
      ["Capital structure", "Delivered with gaps", "5.6", "16.0", "10.4"],
      ["Recovery", "Not assessable", "14.4", null, null],
      ["Peer comparison", "Delivered with gaps", "16.8", "25.6", "8.8"],
      ["Forecast", "Delivered", "26.4", "37.6", "11.2"],
    ]);
    expect(record?.timings.note).toBe(
      "From start to accepted, 13 Nov 2026. Six of thirteen shown.",
    );
  });

  it("reads the mock's hashes, spend, model calls and registers as delivered", () => {
    const record = read()[0]?.record;
    expect(record?.hashes.items.map((i) => [i.label, i.kind, i.value, i.copyLabel])).toEqual([
      [
        "Method texts",
        "SHA-256",
        "71c0e5a9d3b84f2607e1c9a5d3b7f1e9058c6a4e2d0b9f7d5c3a1e9f7b5d3c1a",
        "Copy hash",
      ],
      [
        "Model configuration",
        "Config",
        "copilot-sol-medium · gpt-6-sol",
        "Copy configuration name",
      ],
    ]);
    expect(record?.spend.progress).toEqual({
      text: "USD 11.40 of USD 20.00",
      value: 11.4,
      max: 20,
    });
    expect(record?.calls.count).toBe("41");
    expect(record?.calls.rows.map((r) => r.label)).toEqual([
      "Business profile",
      "Capital structure",
      "Recovery",
      "Peer comparison",
    ]);
    expect(record?.calls.total.label).toBe("Total");
    expect(record?.registers.count).toBe("5");
    expect(record?.registers.rows.map((r) => [r.name, r.writtenBy, r.rows, r.file])).toEqual([
      ["Source register", "Every module", "212", "registers/sources.md"],
      ["Calculation register", "Financial kernel", "148", "registers/calculations.md"],
      ["Gap ledger", "Every module", "7", "registers/gaps.md"],
      ["Assumption register", "Forecast", "23", "registers/assumptions.md"],
      ["Withheld register", "Delivery", "2", "registers/withheld.md"],
    ]);
    expect(record?.registers.downloadAll.href).not.toBeNull();
    expect(record?.registers.rows.map((r) => r.href === null)).toEqual([
      false,
      false,
      false,
      false,
      true,
    ]);
  });

  it("reads every run that has evidence with a record and a jump list", () => {
    const runs = read();
    expect(runs.map((e) => e?.record.timings.rows.length)).toEqual([6, undefined, 1, 1]);
    expect(runs[2]?.record.timings.rows.map((r) => [r.state, r.started, r.took])).toEqual([
      ["Not run", null, null],
    ]);
    expect(runs[2]?.record.registers.downloadAll.href).toBeNull();
    expect(runs[2]?.record.registers.downloadAll.reason).toContain("not packed");
  });

  const broken: [string, (e: Evidence) => void, string][] = [
    ["no record", (e) => delete (e as Json)["record"], "record"],
    [
      "a timings table with no row and no sentence saying why",
      (e) => (e.record.timings.rows = []),
      "record.timings.emptyText",
    ],
    [
      "a timings table with rows and a sentence saying there are none",
      (e) => (e.record.timings["emptyText"] = "No module ran."),
      "record.timings.emptyText",
    ],
    [
      "an empty timings table for a run that holds its modules",
      (e) => {
        e.record.timings.rows = [];
        e.record.timings["emptyText"] = "No module ran.";
      },
      "record.timings.rows",
    ],
    [
      "a timing that is a blank text",
      (e) => (cellAt(e.record.timings.rows, 1, "started")["text"] = ""),
      "record.timings.rows[1].started.text",
    ],
    [
      "a state no module has",
      (e) => ((e.record.timings.rows[3] as Json)["state"] = "Finished"),
      "record.timings.rows[3].state",
    ],
    [
      "a state that is not the module's own",
      (e) => ((e.record.timings.rows[2] as Json)["state"] = "Delivered"),
      "record.timings.rows[2].state",
    ],
    [
      "a module the run does not hold",
      (e) => ((e.record.timings.rows[0] as Json)["module"] = "Treasury"),
      "record.timings.rows[0].module",
    ],
    [
      "a spend above its cap",
      (e) => (e.record.spend.progress["value"] = 21),
      "record.spend.progress.value",
    ],
    [
      "a model-calls row with a cell too few",
      (e) => ((e.record.calls.rows[0] as Json)["cells"] = [null]),
      "record.calls.rows[0].cells",
    ],
    [
      "a model-calls cell that is a blank text",
      (e) => (((e.record.calls.rows[0] as Json)["cells"] as unknown[])[1] = ""),
      "record.calls.rows[0].cells[1]",
    ],
    ["a model-calls table with no row", (e) => (e.record.calls.rows = []), "record.calls.rows"],
    [
      "a total row with the wrong number of cells",
      (e) => (e.record.calls.total["cells"] = []),
      "record.calls.total.cells",
    ],
    [
      "a register with no address and no reason",
      (e) => ((e.record.registers.rows[4] as Json)["reason"] = null),
      "record.registers.rows[4].reason",
    ],
    ["a register with no rows", (e) => (e.record.registers.rows = []), "record.registers.rows"],
    [
      "a timings head missing",
      (e) => ((e.record.timings["columns"] as unknown[]).length = 4),
      "record.timings.columns",
    ],
    [
      "a model-calls table with a single head",
      (e) => (e.record.calls["columns"] = ["Module"]),
      "record.calls.columns",
    ],
    [
      "a hash that is blank",
      (e) => ((e.record.hashes.items[0] as Json)["value"] = ""),
      "record.hashes.items[0].value",
    ],
  ];
  it.each(broken)("is invalid for %s, with its path", (_, edit, expected) => {
    const slice = fresh();
    edit(evidenceOf(slice));
    expect(reasonOf(slice)).toContain(`${at}.${expected}`);
  });
});
