import { readFileSync } from "node:fs";
import path from "node:path";

/**
 * Each loaded run of the fixture must agree with itself across its pages: the Summary against the
 * Gaps tab, the Trace tab against the traces that open its rows, and the gap ids of both tabs.
 * Every expectation is a delivered string read from the fixture or the mock's own text.
 */
type Json = Record<string, unknown>;
type TraceRow = {
  id: string;
  item: string;
  module: string;
  moduleId: string | null;
  kind: string;
  value: unknown;
};
type Trace = { heading: string; statement: string; evidenceItem: string };
type Gap = { id: string; moduleId: string };
type Run = {
  id: string;
  loading: boolean;
  traces: Record<string, Trace>;
  modules: unknown;
  overview: unknown;
  evidence: {
    tabs: { trace: string; gaps: string };
    trace: { rows: TraceRow[]; emptyText?: string };
    gaps: { groups: { severity: string; count: string; rows: Gap[] }[] };
    summary: { counts: { label: string; value: { text: string }; note: string }[] };
  };
};

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: { issuers: { runs: Run[] }[] } };
const loaded = (fixture.slice.issuers[0]?.runs ?? []).filter((run) => !run.loading);
const fullRun = (): Run => {
  const run = loaded[0];
  if (run === undefined) throw new RangeError("no loaded run");
  return run;
};
const count = (run: Run, label: string) => {
  const found = run.evidence.summary.counts.find((c) => c.label === label);
  if (found === undefined) throw new RangeError(`no ${label} count`);
  return found;
};
const rowOf = (run: Run, id: string): TraceRow => {
  const found = run.evidence.trace.rows.find((row) => row.id === id);
  if (found === undefined) throw new RangeError(`no trace row ${id}`);
  return found;
};
const traceOf = (run: Run, key: string): Trace => {
  const found = run.traces[key];
  if (found === undefined) throw new RangeError(`no trace ${key}`);
  return found;
};

/** Every object that carries a trace key and a title (a chart, a table card), by walking the JSON. */
function titled(node: unknown, found: { title: string; trace: string }[] = []) {
  if (Array.isArray(node)) {
    for (const item of node) titled(item, found);
  } else if (node !== null && typeof node === "object") {
    const o = node as Json;
    if (typeof o["trace"] === "string" && typeof o["title"] === "string") {
      found.push({ title: o["title"], trace: o["trace"] });
    }
    for (const value of Object.values(o)) titled(value, found);
  }
  return found;
}

/**
 * The form of a delivered Cell: missing, withheld, gap or value. The text of a value is not
 * compared: the Trace register adds the unit ("USD 2,105m"), the page shows the mock's own figure text ("2,105").
 */
function form(cell: unknown): string {
  return cell === null ? "missing" : String((cell as { kind?: string }).kind);
}

/** Every object of a page that carries a trace key and a Cell-valued `value`, with where it sits. */
function traced(node: unknown, at: string, found: { at: string; trace: string; value: unknown }[]) {
  if (Array.isArray(node)) {
    node.forEach((item, i) => traced(item, `${at}[${String(i)}]`, found));
  } else if (node !== null && typeof node === "object") {
    const o = node as Json;
    if (typeof o["trace"] === "string" && "value" in o && typeof o["value"] === "object") {
      found.push({ at, trace: o["trace"], value: o["value"] });
    }
    for (const [key, value] of Object.entries(o)) traced(value, `${at}.${key}`, found);
  }
  return found;
}

describe("the fixture's runs agree with themselves", () => {
  it("draws a traced figure in the form of the Trace row its trace opens: missing, withheld, gap or value", () => {
    for (const run of loaded) {
      const cells = traced({ modules: run.modules, overview: run.overview }, "", []);
      if (run === fullRun()) expect(cells.length).toBeGreaterThan(10);
      for (const cell of cells) {
        const trace = run.traces[cell.trace];
        if (trace === undefined) continue;
        const row = rowOf(run, trace.evidenceItem);
        // A trace that several cells share (one facility's terms) names the group, not one figure.
        if (cells.filter((c) => c.trace === cell.trace).length > 1) continue;
        expect(form(row.value), `${run.id} ${cell.trace} ${row.id} ${cell.at}`).toBe(
          form(cell.value),
        );
      }
    }
  });

  it("has a Summary gaps note that names each Gaps group's delivered count and severity word", () => {
    for (const run of loaded) {
      const groups = run.evidence.gaps.groups.map((g) => `${g.count} ${g.severity.toLowerCase()}`);
      expect(count(run, "Gaps").note, run.id).toBe(groups.join(", "));
    }
  });

  it("gives a gap one id on both tabs: a trace row named G- is a gap of the Gaps tab, in the same module", () => {
    for (const run of loaded) {
      const gaps = new Map(run.evidence.gaps.groups.flatMap((g) => g.rows).map((g) => [g.id, g]));
      for (const row of run.evidence.trace.rows.filter((r) => r.id.startsWith("G-"))) {
        expect(gaps.get(row.id)?.moduleId, `${run.id} ${row.id}`).toBe(row.moduleId);
      }
    }
    const run = fullRun();
    expect(
      ["G-01", "G-02", "G-03", "G-04", "G-05", "G-07"].map((id) => [id, rowOf(run, id).item]),
    ).toEqual([
      ["G-01", "The security and intercreditor documents were not provided."],
      ["G-02", "The hedge schedule was not among the files provided."],
      [
        "G-03",
        "Peer figures for two companies are on a reported basis while the issuer is company-adjusted.",
      ],
      [
        "G-04",
        "The share of revenue under cost pass-through clauses is not established for this run.",
      ],
      ["G-05", "The only source for the average cost of debt is marked confidential."],
      [
        "G-07",
        "The lease maturity schedule is not in the files, so leases appear in the stack but not by year.",
      ],
    ]);
  });

  it("opens, with each trace, the row that names the trace's own item (the mock's seven rows included)", () => {
    const run = fullRun();
    const mock: [string, string, string][] = [
      ["net-leverage", "T-0014", "Net leverage 4.6x"],
      ["interest-cover", "T-0015", "Interest cover 2.4x"],
      [
        "bp-finding-1",
        "T-0032",
        "Parts and repair bring 44% of revenue and about three fifths of gross profit.",
      ],
      [
        "bp-finding-3",
        "T-0031",
        "Three customers bring 58% of revenue and one engine programme 34%.",
      ],
      ["cs-maturities", "T-0047", "Maturities by year"],
      ["cs-receivables", "T-0052", "Receivables facility availability"],
    ];
    for (const [key, id, item] of mock) {
      expect(traceOf(run, key).evidenceItem, key).toBe(id);
      expect(rowOf(run, id).item, id).toBe(item);
    }
    expect(rowOf(run, "T-0001").item).toBe(
      "Stable credit with thin headroom: leverage is falling, but the 2028 notes need refinancing.",
    );
    expect(traceOf(run, "bottom-line").evidenceItem).toBe("T-0001");
    for (const [key, trace] of Object.entries(run.traces)) {
      if (key === "bottom-line") continue;
      const item = rowOf(run, trace.evidenceItem).item;
      expect([trace.heading, trace.statement], key).toContain(item);
    }
  });

  it("draws a chart's trace from the row that holds the chart's delivered title, one row for each chart", () => {
    const run = fullRun();
    const charts = run.evidence.trace.rows.filter((r) => r.kind === "Chart");
    const cards = titled(run.modules);
    expect(charts.map((r) => r.id)).toEqual([
      "T-0047",
      "T-0114",
      "T-0116",
      "T-0117",
      "T-0118",
      "T-0119",
    ]);
    for (const chart of charts) {
      const cardTraces = cards.filter((c) => c.title === chart.item).map((c) => c.trace);
      expect(cardTraces, chart.item).toHaveLength(1);
      expect(traceOf(run, cardTraces[0] ?? "").evidenceItem, chart.item).toBe(chart.id);
    }
    const items = run.evidence.trace.rows.map((r) => `${r.moduleId ?? ""}|${r.item}`);
    expect(rowOf(run, "T-0119").item).not.toBe(rowOf(run, "T-0015").item);
    expect(rowOf(run, "T-0119").item).not.toBe(rowOf(run, "T-0108").item);
    expect(
      items.filter((item) => item.endsWith("|Interest cover against the peer range")),
    ).toHaveLength(1);
  });

  it("opens every row but the no-source claim from at least one trace, and counts the rows it holds", () => {
    for (const run of loaded) {
      const opened = new Set(Object.values(run.traces).map((t) => t.evidenceItem));
      const orphans = run.evidence.trace.rows.filter((r) => !opened.has(r.id)).map((r) => r.id);
      expect(orphans, run.id).toEqual(run.evidence.trace.rows.length === 0 ? [] : ["T-0068"]);
      const rows = String(run.evidence.trace.rows.length);
      expect(run.evidence.tabs.trace, run.id).toBe(rows);
      expect(count(run, "Calculations").value.text, run.id).toBe(rows);
    }
    expect(fullRun().evidence.trace.rows).toHaveLength(59);
    expect(count(fullRun(), "Calculations").note).toBe("Each one traceable to its inputs");
    for (const run of loaded.filter((r) => r.evidence.trace.rows.length === 0)) {
      expect(count(run, "Calculations").note, run.id).toBe("Not traced item by item in this run");
      expect(run.evidence.trace.emptyText, run.id).toContain("not traced item by item");
    }
  });

  it("tells the risks apart: a risk or indicator row carries its trace's own statement", () => {
    const run = fullRun();
    for (const [key, trace] of Object.entries(run.traces)) {
      if (!/^bp-(risk|watch)-\d$/.test(key)) continue;
      expect(rowOf(run, trace.evidenceItem).item, key).toBe(trace.statement);
    }
    expect(rowOf(run, "T-0053").item).toBe(
      "Engine programme delay: Medium probability, high impact.",
    );
    expect(rowOf(run, "T-0055").item).not.toBe(rowOf(run, "T-0053").item);
  });
});
