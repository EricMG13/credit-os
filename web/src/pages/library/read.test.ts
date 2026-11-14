import { readFileSync } from "node:fs";
import path from "node:path";
import { cell, readSlice, traceKey } from "./read";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: Json };

/** A deep copy of the fixture's slice that a test can break. */
function fresh(): { home: { cards: Json[]; filters: Json } & Json; issuers: Json[] } {
  return structuredClone(fixture.slice) as ReturnType<typeof fresh>;
}

type Card = Json & { measures: Json };
const cardAt = (slice: ReturnType<typeof fresh>, i: number) => slice.home.cards[i] as Card;

function invalidReason(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

describe("readSlice", () => {
  it("reads the fixture's slice as ok", () => {
    const result = readSlice(fixture.slice);
    expect(result.kind).toBe("ok");
    if (result.kind === "ok") {
      expect(result.data.home.cards).toHaveLength(6);
      expect(result.data.issuers.map((issuer) => issuer.name)).toContain("Lumora Health");
    }
  });

  it("is absent when the data file has no library member", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });

  it.each([
    ["a slice that is not an object", "text", "slice"],
    ["a missing home", { issuers: [] }, "home"],
  ])("is invalid for %s, naming %s", (_, source, path) => {
    expect(invalidReason(source)).toContain(path);
  });

  it("names the exact path of a malformed card field", () => {
    const slice = fresh();
    slice.home.cards[1] = { ...slice.home.cards[1], note: 7 };
    expect(invalidReason(slice)).toContain("home.cards[1].note");
  });

  it("names the path of a malformed nested progress value", () => {
    const slice = fresh();
    slice.home.cards[2] = {
      ...slice.home.cards[2],
      progress: { text: "6 of 6", value: "6", max: 6 },
    };
    expect(invalidReason(slice)).toContain("home.cards[2].progress.value");
  });

  it("rejects a progress value beyond its max", () => {
    const slice = fresh();
    slice.home.cards[0] = { ...slice.home.cards[0], progress: { text: "x", value: 14, max: 13 } };
    expect(invalidReason(slice)).toContain("home.cards[0].progress.value");
  });

  it("rejects a state outside the run states", () => {
    const slice = fresh();
    slice.home.cards[3] = { ...slice.home.cards[3], state: "Done" };
    expect(invalidReason(slice)).toContain("home.cards[3].state");
  });

  it("rejects an unknown card kind", () => {
    const slice = fresh();
    slice.home.cards[5] = { kind: "other" };
    expect(invalidReason(slice)).toContain("home.cards[5].kind");
  });

  it("rejects a card whose issuer is not in the issuer list", () => {
    const slice = fresh();
    slice.home.cards[0] = { ...slice.home.cards[0], issuer: "nobody" };
    expect(invalidReason(slice)).toContain("home.cards[0].issuer");
  });

  it("rejects an href that is missing rather than null", () => {
    const slice = fresh();
    const noHref = { ...slice.home.cards[0] };
    delete noHref["href"];
    slice.home.cards[0] = noHref;
    expect(invalidReason(slice)).toContain("home.cards[0].href");
  });

  it("rejects a filter list that holds a non-string", () => {
    const slice = fresh();
    slice.home.filters["sector"] = ["Rigid packaging", 3];
    expect(invalidReason(slice)).toContain("home.filters.sector[1]");
  });

  it("requires one applied-count label for zero to seven filters", () => {
    const slice = fresh();
    slice.home.filters["appliedLabels"] = ["No filter applied"];
    expect(invalidReason(slice)).toContain("home.filters.appliedLabels");
  });

  it("names the path of a malformed issuer record", () => {
    const slice = fresh();
    slice.issuers[2] = { id: "tessaly-foods" };
    expect(invalidReason(slice)).toContain("issuers[2].name");
  });

  it("does not read a prototype property as a field", () => {
    const slice = fresh();
    const card = Object.create({ kind: "loading" }) as Json;
    slice.home.cards[5] = card;
    expect(invalidReason(slice)).toContain("home.cards[5].kind");
  });
});

describe("cell", () => {
  const read = (value: unknown) => cell({ c: value }, "c", "row");

  it.each([
    ["missing", null],
    ["a value with a position", { kind: "value", text: "4.2x", at: 4.2 }],
    ["a value without one", { kind: "value", text: "n/m", at: null }],
    ["a withheld value with a reason", { kind: "withheld", reason: "Under embargo" }],
    ["a withheld value without a reason", { kind: "withheld", reason: null }],
    ["a gap", { kind: "gap", reason: "Not in the files provided" }],
  ])("reads %s as written", (_, value) => {
    expect(read(value)).toEqual(value);
  });

  it("does not turn an absent field into missing", () => {
    expect(() => cell({}, "c", "row")).toThrow("row.c");
  });

  it.each([
    ["an unknown kind", { kind: "zero", text: "0" }, "row.c.kind"],
    ["a value with no text", { kind: "value", at: 1 }, "row.c.text"],
    ["a value whose position is a string", { kind: "value", text: "1", at: "1" }, "row.c.at"],
    ["a gap with no reason", { kind: "gap", reason: null }, "row.c.reason"],
    ["a number where a cell belongs", 0, "row.c"],
  ])("rejects %s at its path", (_, value, where) => {
    expect(() => read(value)).toThrow(where);
  });
});

describe("readSlice, the List side", () => {
  it("names the path of a malformed measure figure", () => {
    const slice = fresh();
    const card = cardAt(slice, 0);
    card.measures = { ...card.measures, netLeverage: { text: "2.9x", at: "2.9" } };
    expect(invalidReason(slice)).toContain("home.cards[0].measures.netLeverage.at");
  });

  it("rejects a basis that is neither reported nor adjusted", () => {
    const slice = fresh();
    const card = cardAt(slice, 2);
    card.measures = {
      ...card.measures,
      leverage: { text: "5.6x", at: 5.6, basis: "estimated", description: "x" },
    };
    expect(invalidReason(slice)).toContain("home.cards[2].measures.leverage.basis");
  });

  it("takes an explicit null measure as not recorded, and an absent one as malformed", () => {
    const slice = fresh();
    expect(cardAt(slice, 4).measures).toMatchObject({ leverage: null, netLeverage: null });
    delete cardAt(slice, 4).measures.leverage;
    expect(invalidReason(slice)).toContain("home.cards[4].measures.leverage");
  });

  it("names the path of a band whose range is reversed, and of a missing list", () => {
    const slice = fresh();
    const specs = (slice.home as unknown as { list: { measures: Record<string, Json> } }).list
      .measures;
    specs.leverage = {
      ...specs.leverage,
      bands: [{ label: "Bad", min: 5, max: 3 }],
    };
    expect(invalidReason(slice)).toContain("home.list.measures.leverage.bands[0].max");
    specs.leverage = {
      ...specs.leverage,
      bands: [
        { label: "Low", min: null, max: 3 },
        { label: "Low", min: 3, max: null },
      ],
    };
    expect(invalidReason(slice)).toContain("home.list.measures.leverage.bands[1].label");
    const bare = fresh();
    delete (bare.home as Json).list;
    expect(invalidReason(bare)).toContain("home.list");
  });
});

describe("readSlice, issuer history", () => {
  type History = Json & { entries: Json[] };
  const historyOf = (slice: ReturnType<typeof fresh>, i: number) =>
    slice.issuers[i]?.["history"] as History;

  it("names the exact path of a malformed entry's changes link", () => {
    const slice = fresh();
    historyOf(slice, 0).entries[1] = {
      ...historyOf(slice, 0).entries[1],
      changes: { label: "What changed", run: 3 },
    };
    expect(invalidReason(slice)).toContain("issuers[0].history.entries[1].changes.run");
  });

  it("rejects a history missing from an issuer", () => {
    const slice = fresh();
    delete slice.issuers[2]?.["history"];
    expect(invalidReason(slice)).toContain("issuers[2].history");
  });

  it("rejects a latest run no entry opens", () => {
    const slice = fresh();
    historyOf(slice, 0)["latest"] = "2031-01-01";
    expect(invalidReason(slice)).toContain("issuers[0].history.latest");
  });

  it("rejects no latest run without the sentence, and a sentence beside a latest run", () => {
    const none = fresh();
    historyOf(none, 5)["empty"] = null;
    expect(invalidReason(none)).toContain("issuers[5].history.empty");
    const both = fresh();
    historyOf(both, 0)["empty"] = "Nothing to read.";
    expect(invalidReason(both)).toContain("issuers[0].history.empty");
  });

  it.each(["Failed", "Rejected", "Interrupted", "Running", "Queued"])(
    "rejects a report or changes link on a %s entry, naming the field",
    (state) => {
      const withReport = fresh();
      historyOf(withReport, 0).entries[4] = {
        ...historyOf(withReport, 0).entries[4],
        state,
        report: "2025-12-31",
      };
      expect(invalidReason(withReport)).toContain("issuers[0].history.entries[4].report");
      const withChanges = fresh();
      historyOf(withChanges, 0).entries[4] = {
        ...historyOf(withChanges, 0).entries[4],
        state,
        changes: { label: "What changed", run: "2025-12-31" },
      };
      expect(invalidReason(withChanges)).toContain("issuers[0].history.entries[4].changes");
    },
  );

  it.each(["Finished", "Capped"])("accepts a report and changes link on a %s entry", (state) => {
    const slice = fresh();
    historyOf(slice, 0).entries[4] = {
      ...historyOf(slice, 0).entries[4],
      state,
      report: "2025-12-31",
      changes: { label: "What changed", run: "2025-12-31" },
    };
    expect(readSlice(slice).kind).toBe("ok");
  });

  it("rejects two entries with the same asOf and ran, naming the second", () => {
    const slice = fresh();
    const entries = historyOf(slice, 0).entries;
    entries[1] = { ...entries[1], asOf: entries[0]?.["asOf"], ran: entries[0]?.["ran"] };
    expect(invalidReason(slice)).toContain("issuers[0].history.entries[1]");
  });
});

describe("readSlice, run frame", () => {
  type Run = Json & { head: Json; traces: Record<string, Json & { derivation: Json }> };
  const runOf = (slice: ReturnType<typeof fresh>, i: number, r: number) =>
    (slice.issuers[i]?.["runs"] as Run[])[r] as Run;

  it("reads Halden's two runs, the second still loading, with its trace tree", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const [head, loading] = result.data.issuers[0]?.runs ?? [];
    expect(head?.head).toMatchObject({ issuerName: "Halden Aerostructures", state: "Finished" });
    expect(head?.loading).toBe(false);
    expect(head?.traces["net-leverage"]?.derivation.children[0]?.label).toBe("Formula");
    expect(loading?.loading).toBe(true);
  });

  it("names the path of a malformed head field", () => {
    const slice = fresh();
    runOf(slice, 0, 0).head["forecastHref"] = 4;
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].head.forecastHref");
  });

  it("names the path of a malformed tree node deep in a trace", () => {
    const slice = fresh();
    const tree = runOf(slice, 0, 0).traces["net-leverage"]?.derivation as Json & {
      children: Json[];
    };
    (tree.children[0] as Json & { children: Json[] }).children[0] = { label: "Input", value: 3 };
    expect(invalidReason(slice)).toContain(
      "issuers[0].runs[0].traces.net-leverage.derivation.children[0].children[0].value",
    );
  });

  it("rejects a trace without its statement, and a run state outside the run states", () => {
    const slice = fresh();
    delete runOf(slice, 0, 0).traces["net-leverage"]?.["statement"];
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].traces.net-leverage.statement");
    const other = fresh();
    runOf(other, 0, 0).head["state"] = "Done";
    expect(invalidReason(other)).toContain("issuers[0].runs[0].head.state");
  });

  it("names the path of a malformed excerpt, and takes a null excerpt and qualification", () => {
    const slice = fresh();
    const trace = runOf(slice, 0, 0).traces["net-leverage"] as Json;
    trace["excerpt"] = { quote: "q", source: 5 };
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].traces.net-leverage.excerpt.source");
    trace["excerpt"] = null;
    trace["qualification"] = null;
    expect(readSlice(slice).kind).toBe("ok");
    delete trace["subtitle"];
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].traces.net-leverage.subtitle");
  });

  it("names the path of a trace with no visible heading", () => {
    const slice = fresh();
    const trace = runOf(slice, 0, 0).traces["net-leverage"] as Json;
    trace["heading"] = 4;
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].traces.net-leverage.heading");
  });

  it("rejects two runs with one id and an issuer with no runs list", () => {
    const slice = fresh();
    (slice.issuers[0] as Json)["runs"] = [runOf(slice, 0, 0), runOf(slice, 0, 0)];
    expect(invalidReason(slice)).toContain("issuers[0].runs[1].id");
    const bare = fresh();
    delete (bare.issuers[1] as Json)["runs"];
    expect(invalidReason(bare)).toContain("issuers[1].runs");
  });

  it("does not read a prototype property as a trace", () => {
    const slice = fresh();
    runOf(slice, 0, 0)["overview"] = runOf(slice, 0, 2)["overview"];
    runOf(slice, 0, 0)["changes"] = runOf(slice, 0, 2)["changes"];
    runOf(slice, 0, 0)["modules"] = runOf(slice, 0, 2)["modules"];
    runOf(slice, 0, 0).traces = Object.create({ x: {} }) as Run["traces"];
    const result = readSlice(slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(Object.keys(result.data.issuers[0]?.runs[0]?.traces ?? {})).toEqual([]);
  });
});

describe("traceKey", () => {
  const traces = { "net-leverage": {} } as never;

  it("reads a key the run holds and a null as no trace", () => {
    expect(traceKey({ trace: "net-leverage" }, "trace", "p", traces)).toBe("net-leverage");
    expect(traceKey({ trace: null }, "trace", "p", traces)).toBeNull();
  });

  it("is invalid, with the item's path, for a key the run does not hold or a wrong type", () => {
    expect(() => traceKey({ trace: "ghost" }, "trace", "p.metrics[1]", traces)).toThrow(
      "p.metrics[1].trace: expected a key of the run's traces",
    );
    expect(() => traceKey({ trace: 3 }, "trace", "p", traces)).toThrow("p.trace");
    expect(() => traceKey({ trace: "toString" }, "trace", "p", traces)).toThrow("p.trace");
  });
});

describe("readSlice, overview", () => {
  type Ov = {
    bottomLine: Json;
    metrics: Json[];
    sides: { columns: { items: Json[] }[] };
    findings: Json[];
    changeView: Json;
    dates: Json[];
    modules: { items: Json[] } & Json;
    limitations: { items: Json[]; gapsLink: Json } & Json;
  };
  type Run = Json & { overview: Ov | null };
  const runOf = (slice: ReturnType<typeof fresh>, r: number) =>
    (slice.issuers[0]?.["runs"] as Run[])[r] as Run;
  const ovOf = (slice: ReturnType<typeof fresh>) => runOf(slice, 0).overview as Ov;

  it("reads the mock's overview: the loading run has none, the zero metric stays zero", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const [full, loading, capped] = result.data.issuers[0]?.runs ?? [];
    expect(loading?.overview).toBeNull();
    if (full?.loading !== false || capped?.loading !== false) throw new Error("runs are loaded");
    expect(full.overview.metrics).toHaveLength(6);
    expect(full.overview.metrics[5]?.value).toBeNull();
    expect(full.overview.sides.columns.map((c) => c.items.length)).toEqual([3, 3]);
    expect(capped.overview.metrics[0]?.value).toEqual({ kind: "value", text: "0", at: 0 });
    expect(capped.overview.metrics[1]?.value).toMatchObject({ kind: "withheld" });
    expect(full.overview.findings.map((f) => f.number)).toEqual(["01", "02", "03", "04", "05"]);
    expect(full.overview.dates.map((d) => d.state)).toEqual(["Past", "Next", "Later", "Later"]);
    expect(full.overview.changeView.title).toBe("Two triggers, either is enough");
    expect(capped.overview.changeView.trace).toBeNull();
    expect(full.overview.modules.items).toHaveLength(13);
    expect(capped.overview.modules.items[0]?.module).toBeNull();
    expect(full.overview.limitations.count).toBe("4");
  });

  it.each([
    [
      "a malformed metric value",
      (o: Ov) => ((o.metrics[1] as Json)["value"] = { kind: "value" }),
      "overview.metrics[1].value.text",
    ],
    [
      "a metric trace the run lacks",
      (o: Ov) => ((o.metrics[0] as Json)["trace"] = "ghost"),
      "overview.metrics[0].trace",
    ],
    [
      "an item trace the run lacks",
      (o: Ov) => ((o.sides.columns[1]?.items[2] as Json)["trace"] = "ghost"),
      "overview.sides.columns[1].items[2].trace",
    ],
    [
      "a bottom line without its lead",
      (o: Ov) => delete o.bottomLine["lead"],
      "overview.bottomLine.lead",
    ],
    [
      "an item without its qualifier",
      (o: Ov) => delete (o.sides.columns[0]?.items[0] as Json)["qualifier"],
      "overview.sides.columns[0].items[0].qualifier",
    ],
    [
      "a finding without its body",
      (o: Ov) => delete (o.findings[2] as Json)["body"],
      "overview.findings[2].body",
    ],
    [
      "a finding trace the run lacks",
      (o: Ov) => ((o.findings[0] as Json)["trace"] = "ghost"),
      "overview.findings[0].trace",
    ],
    [
      "a change view without its text",
      (o: Ov) => delete o.changeView["text"],
      "overview.changeView.text",
    ],
    [
      "a change view trace the run lacks",
      (o: Ov) => (o.changeView["trace"] = "ghost"),
      "overview.changeView.trace",
    ],
    [
      "a date in a state outside Past, Next and Later",
      (o: Ov) => ((o.dates[1] as Json)["state"] = "Soon"),
      "overview.dates[1].state",
    ],
    [
      "a module item in a state outside the Module state set",
      (o: Ov) => ((o.modules.items[1] as Json)["state"] = "Done"),
      "overview.modules.items[1].state",
    ],
    [
      "a module item without its module field",
      (o: Ov) => delete (o.modules.items[0] as Json)["module"],
      "overview.modules.items[0].module",
    ],
    [
      "a repeated module item",
      (o: Ov) => (o.modules.items[2] = { ...o.modules.items[1] }),
      "overview.modules.items[2].title",
    ],
    [
      "limitations without the gaps link label",
      (o: Ov) => delete o.limitations.gapsLink["label"],
      "overview.limitations.gapsLink.label",
    ],
    [
      "a limitation trace the run lacks",
      (o: Ov) => ((o.limitations.items[0] as Json)["trace"] = "ghost"),
      "overview.limitations.items[0].trace",
    ],
    [
      "a repeated finding number",
      (o: Ov) => ((o.findings[1] as Json)["number"] = "01"),
      "overview.findings[1].number",
    ],
    [
      "a repeated date and title",
      (o: Ov) => (o.dates[3] = { ...o.dates[2] }),
      "overview.dates[3].title",
    ],
  ])("is invalid for %s, with its path", (_, break_, path) => {
    const slice = fresh();
    break_(ovOf(slice));
    expect(invalidReason(slice)).toContain(`issuers[0].runs[0].${path}`);
  });

  it("rejects a finished run with no overview and a loading run that carries one", () => {
    const missing = fresh();
    runOf(missing, 0).overview = null;
    expect(invalidReason(missing)).toContain("issuers[0].runs[0].overview");
    const loaded = fresh();
    runOf(loaded, 1).overview = ovOf(fresh());
    expect(invalidReason(loaded)).toContain("issuers[0].runs[1].overview");
  });

  it("rejects a repeated metric label, a repeated point in a column and a column count not two", () => {
    const labels = fresh();
    ovOf(labels).metrics[1] = { ...ovOf(labels).metrics[0] };
    expect(invalidReason(labels)).toContain("issuers[0].runs[0].overview.metrics[1].label");
    const texts = fresh();
    const items = ovOf(texts).sides.columns[0]?.items as Json[];
    items[1] = { ...items[0] };
    expect(invalidReason(texts)).toContain(
      "issuers[0].runs[0].overview.sides.columns[0].items[1].text",
    );
    const columns = fresh();
    ovOf(columns).sides.columns.pop();
    expect(invalidReason(columns)).toContain("issuers[0].runs[0].overview.sides.columns");
  });
});

describe("readSlice, an overview with nothing to draw", () => {
  type Ov = {
    findings: Json[];
    dates: Json[];
    modules: { items: Json[] };
    limitations: { items: Json[] };
    sides: { columns: { items: Json[] }[] };
  };
  const ovOf = (slice: ReturnType<typeof fresh>) =>
    ((slice.issuers[0]?.["runs"] as { overview: Ov }[])[0] as { overview: Ov }).overview;

  it.each([
    ["findings", (o: Ov) => (o.findings.length = 0), "overview.findings"],
    ["dates", (o: Ov) => (o.dates.length = 0), "overview.dates"],
    ["module items", (o: Ov) => (o.modules.items.length = 0), "overview.modules.items"],
    ["limitation items", (o: Ov) => (o.limitations.items.length = 0), "overview.limitations.items"],
    [
      "the first column's points",
      (o: Ov) => ((o.sides.columns[0] as { items: Json[] }).items.length = 0),
      "overview.sides.columns[0].items",
    ],
    [
      "the second column's points",
      (o: Ov) => ((o.sides.columns[1] as { items: Json[] }).items.length = 0),
      "overview.sides.columns[1].items",
    ],
  ])("rejects empty %s with the path of the list", (_, empty, path) => {
    const slice = fresh();
    empty(ovOf(slice));
    expect(invalidReason(slice)).toContain(`issuers[0].runs[0].${path}`);
  });
});

describe("readSlice, changes", () => {
  type Run = Json & { changes: Json | null };
  type Compared = Json & { changes: (Json & { from: unknown })[]; modules: { items: Json[] } };
  const runOf = (slice: ReturnType<typeof fresh>, r: number) =>
    (slice.issuers[0]?.["runs"] as Run[])[r] as Run;
  const comparedOf = (slice: ReturnType<typeof fresh>) => runOf(slice, 0).changes as Compared;

  const changeAt = (slice: ReturnType<typeof fresh>, i: number): Json => {
    const found = comparedOf(slice).changes[i];
    if (found === undefined) throw new Error(`no change ${String(i)}`);
    return found;
  };
  const itemAt = (slice: ReturnType<typeof fresh>, i: number): Json => {
    const found = comparedOf(slice).modules.items[i];
    if (found === undefined) throw new Error(`no module item ${String(i)}`);
    return found;
  };

  it("reads the compared run, the first run's none, and a loading run's null", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const runs = result.data.issuers[0]?.runs ?? [];
    const first = runs[0]?.changes;
    expect(first?.kind).toBe("compared");
    if (first?.kind !== "compared") throw new Error("not compared");
    expect(first.changes.map((c) => c.measure)).toHaveLength(6);
    expect(first.changes[3]?.from).toBeNull();
    expect(first.changes[3]?.direction).toBe("none");
    expect(runs[1]?.changes).toBeNull();
    expect(runs[3]?.changes).toMatchObject({ kind: "none", title: "No earlier run to compare" });
  });

  it("names the path of a malformed change field", () => {
    const direction = fresh();
    changeAt(direction, 0)["direction"] = "sideways";
    expect(invalidReason(direction)).toContain("issuers[0].runs[0].changes.changes[0].direction");
    const cause = fresh();
    delete changeAt(cause, 2)["cause"];
    expect(invalidReason(cause)).toContain("issuers[0].runs[0].changes.changes[2].cause");
    const kind = fresh();
    (runOf(kind, 0).changes as Json)["kind"] = "later";
    expect(invalidReason(kind)).toContain("issuers[0].runs[0].changes.kind");
  });

  it("rejects a blank figure text, which the table cannot draw, but keeps a zero", () => {
    const blank = fresh();
    changeAt(blank, 0)["current"] = { kind: "value", text: "", at: null };
    expect(invalidReason(blank)).toContain("issuers[0].runs[0].changes.changes[0].current.text");
    const earlier = fresh();
    changeAt(earlier, 1)["from"] = { kind: "value", text: "", at: null };
    expect(invalidReason(earlier)).toContain("issuers[0].runs[0].changes.changes[1].from.text");
    expect(readSlice(fixture.slice).kind).toBe("ok");
  });

  it("rejects a direction or change text beside a missing earlier figure", () => {
    const dir = fresh();
    changeAt(dir, 3)["direction"] = "up";
    expect(invalidReason(dir)).toContain("issuers[0].runs[0].changes.changes[3].direction");
    const text = fresh();
    changeAt(text, 3)["change"] = "Higher by 2.4x";
    expect(invalidReason(text)).toContain("issuers[0].runs[0].changes.changes[3].change");
  });

  it("rejects a direction mark with no delivered words", () => {
    const slice = fresh();
    changeAt(slice, 0)["change"] = null;
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].changes.changes[0].change");
  });

  it("needs both figures as values for a direction mark, with the path of the failing field", () => {
    const missing = fresh();
    changeAt(missing, 0)["current"] = null;
    expect(invalidReason(missing)).toContain("issuers[0].runs[0].changes.changes[0].direction");
    const withheld = fresh();
    changeAt(withheld, 1)["from"] = { kind: "withheld", reason: null };
    expect(invalidReason(withheld)).toContain("issuers[0].runs[0].changes.changes[1].direction");
    const gap = fresh();
    changeAt(gap, 0)["current"] = { kind: "gap", reason: "No figure was delivered." };
    expect(invalidReason(gap)).toContain("issuers[0].runs[0].changes.changes[0].direction");
    const text = fresh();
    const unmarked = changeAt(text, 0);
    unmarked["current"] = null;
    unmarked["direction"] = "none";
    expect(invalidReason(text)).toContain("issuers[0].runs[0].changes.changes[0].change");
    unmarked["change"] = null;
    expect(readSlice(text).kind).toBe("ok");
  });

  it("rejects an empty change text and reads the delivered flat direction", () => {
    const blank = fresh();
    changeAt(blank, 1)["change"] = "";
    expect(invalidReason(blank)).toContain("issuers[0].runs[0].changes.changes[1].change");
    const none = fresh();
    changeAt(none, 4)["change"] = "";
    expect(invalidReason(none)).toContain("issuers[0].runs[0].changes.changes[4].change");
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const changes = result.data.issuers[0]?.runs[0]?.changes;
    if (changes?.kind !== "compared") throw new Error("not compared");
    expect(changes.changes.map((c) => c.direction)).toEqual([
      "down",
      "up",
      "down",
      "none",
      "flat",
      "flat",
    ]);
    const noText = fresh();
    changeAt(noText, 4)["change"] = null;
    expect(invalidReason(noText)).toContain("issuers[0].runs[0].changes.changes[4].change");
  });

  it("rejects an empty changes list, a repeated measure, a trace the run lacks", () => {
    const empty = fresh();
    comparedOf(empty).changes.length = 0;
    expect(invalidReason(empty)).toContain("issuers[0].runs[0].changes.changes");
    const repeated = fresh();
    changeAt(repeated, 1)["measure"] = changeAt(repeated, 0)["measure"];
    expect(invalidReason(repeated)).toContain("issuers[0].runs[0].changes.changes[1].measure");
    const trace = fresh();
    changeAt(trace, 0)["trace"] = "nothing";
    expect(invalidReason(trace)).toContain("issuers[0].runs[0].changes.changes[0].trace");
  });

  it("names the path of a malformed module item and a state outside the Change state set", () => {
    const state = fresh();
    itemAt(state, 0)["state"] = "Delivered";
    expect(invalidReason(state)).toContain("issuers[0].runs[0].changes.modules.items[0].state");
    const repeated = fresh();
    itemAt(repeated, 1)["title"] = itemAt(repeated, 0)["title"];
    expect(invalidReason(repeated)).toContain("issuers[0].runs[0].changes.modules.items[1].title");
  });

  it("rejects a finished run with no changes and a loading run that carries them", () => {
    const missing = fresh();
    runOf(missing, 0).changes = null;
    expect(invalidReason(missing)).toContain("issuers[0].runs[0].changes");
    const loaded = fresh();
    runOf(loaded, 1).changes = runOf(fresh(), 0).changes;
    expect(invalidReason(loaded)).toContain("issuers[0].runs[1].changes");
  });
});

describe("readSlice, modules", () => {
  type Mod = Json & { body: Json & { records: unknown[] } };
  type Run = Json & { modules: Mod[] | null; head: Json; overview: Json; changes: Json };
  const runOf = (slice: ReturnType<typeof fresh>, r: number) =>
    (slice.issuers[0]?.["runs"] as Run[])[r] as Run;
  const modOf = (slice: ReturnType<typeof fresh>, id: string, r = 0): Mod => {
    const found = runOf(slice, r).modules?.find((m) => m["id"] === id);
    if (found === undefined) throw new Error(`no module ${id}`);
    return found;
  };
  const at = (slice: ReturnType<typeof fresh>, id: string, r = 0) =>
    `issuers[0].runs[${String(r)}].modules[${String(runOf(slice, r).modules?.findIndex((m) => m["id"] === id))}]`;

  const matrix = (s: ReturnType<typeof fresh>) =>
    modOf(s, "business-profile").body.records[0] as Json;
  const matrixRow = (s: ReturnType<typeof fresh>, i: number) =>
    (matrix(s)["rows"] as Json[])[i] as Json;

  const block = (s: ReturnType<typeof fresh>, kind: string) =>
    modOf(s, "business-profile").body.records.find((r) => (r as Json)["kind"] === kind) as Json;
  const item = (s: ReturnType<typeof fresh>, kind: string, i: number) =>
    (block(s, kind)["items"] as Json[])[i] as Json;

  const step = (s: ReturnType<typeof fresh>, i: number) =>
    (block(s, "edges")["steps"] as Json[])[i] as Json;

  it("reads the pathway's four steps as the mock words them", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const body = result.data.issuers[0]?.runs[0]?.modules?.[0]?.body;
    if (body?.kind !== "delivered") throw new Error("not delivered");
    const edges = body.records[3];
    expect(edges?.kind === "edges" && edges.steps.map((x) => [x.title, x.text])).toEqual([
      ["Ramp slips", "Deliveries fall short of plan"],
      ["Inventory stays", "Cash tied up for longer"],
      ["Cash flow falls", "Less debt repaid from operations"],
      ["Leverage holds", "Refinancing on weaker terms"],
    ]);
  });

  it("reads the watch list and the questions as the mock words them", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const body = result.data.issuers[0]?.runs[0]?.modules?.[0]?.body;
    if (body?.kind !== "delivered") throw new Error("not delivered");
    const [, watch, questions] = body.records;
    expect(
      watch?.kind === "watch" && watch.items.map((i) => [i.indicator, i.threshold, i.timing]),
    ).toEqual([
      ["Engine deliveries per month", "Below 40 for two quarters", "leading"],
      ["Aftermarket price rise at renewal", "Below 3%", "leading"],
      ["Alternative parts certified", "Any top-ten part", "leading"],
      ["Aftermarket share of gross profit", "Below 55%", "lagging"],
    ]);
    expect(
      questions?.kind === "questions" && questions.items.map((i) => [i.state, i.answer === null]),
    ).toEqual([
      ["Answered", false],
      ["Partly answered", true],
      ["Not answered", true],
      ["Answered", false],
    ]);
  });

  it("reads the matrix with a missing grade as null, not as a word", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const block = result.data.issuers[0]?.runs[0]?.modules?.[0]?.body;
    if (block?.kind !== "delivered") throw new Error("not delivered");
    expect(block.records[0]).toMatchObject({
      kind: "matrix",
      title: "Risks by probability and impact",
      note: null,
      columns: ["Risk", "Probability", "Impact"],
    });
    const rows = block.records[0]?.kind === "matrix" ? block.records[0].rows : [];
    expect(rows.map((r) => [r.risk, r.probability, r.impact])).toEqual([
      ["Engine programme delay", "Medium", "High"],
      ["Loss of sole-source status", "Low", "High"],
      ["Customer concentration", "Medium", "Medium"],
      ["Input cost inflation", "High", "Low"],
      ["Tariff exposure", null, "Medium"],
    ]);
  });

  it("rejects an Overview item whose state differs from the module it opens, and only that", () => {
    const slice = fresh();
    const items = (runOf(slice, 0).overview["modules"] as { items: Json[] }).items;
    const i = items.findIndex((item) => item["module"] !== null);
    const held = modOf(slice, String((items[i] as Json)["module"]))["state"];
    (items[i] as Json)["state"] = held === "Delivered" ? "Not run" : "Delivered";
    expect(invalidReason(slice)).toContain(
      `issuers[0].runs[0].overview.modules.items[${String(i)}].state`,
    );
    expect(readSlice(fresh()).kind).toBe("ok");
  });

  it("reads thirteen modules for every finished run and a loading run's null", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const runs = result.data.issuers[0]?.runs ?? [];
    const full = runs[0]?.modules ?? [];
    expect(full.map((m) => m.name)).toEqual([
      "Business profile",
      "Industry and competition",
      "Financial performance",
      "Cash flow and liquidity",
      "Capital structure",
      "Covenants and documentation",
      "Management and governance",
      "Peer comparison",
      "Recovery",
      "Rating outlook",
      "Environmental, social and governance",
      "Forecast",
      "Credit snapshot",
    ]);
    expect(full.map((m) => m.state).filter((s) => s !== "Delivered")).toEqual([
      "Delivered with gaps",
      "Delivered with gaps",
      "Not assessable",
    ]);
    expect(full.find((m) => m.id === "recovery")?.body.kind).toBe("blocked");
    expect(full[0]?.body).toMatchObject({ kind: "delivered" });
    expect(full[1]?.body).toMatchObject({ kind: "delivered", records: [] });
    expect(runs[1]?.modules).toBeNull();
    expect(runs[2]?.modules?.map((m) => m.name)).toEqual(full.map((m) => m.name));
    expect(runs[2]?.modules?.map((m) => m.state)).toEqual([
      "Delivered",
      "Delivered",
      "Not run",
      "Not run",
      "Delivered with gaps",
      "Delivered",
      "Delivered",
      "Delivered with gaps",
      "Not run",
      "Delivered",
      "Delivered",
      "Not run",
      "Delivered",
    ]);
    expect(runs[3]?.modules?.map((m) => m.name)).toEqual(full.map((m) => m.name));
    expect(runs[3]?.modules?.map((m) => m.state).filter((s) => s !== "Delivered")).toEqual([
      "Delivered with gaps",
      "Delivered with gaps",
    ]);
    expect(runs.map((r) => r.head.firstModule)).toEqual([
      "business-profile",
      null,
      "business-profile",
      "business-profile",
    ]);
  });

  it.each([
    [
      "a missing bottom line lead",
      (s: ReturnType<typeof fresh>) =>
        delete (modOf(s, "business-profile").body["bottomLine"] as Json)["lead"],
      "business-profile",
      "body.bottomLine.lead",
    ],
    [
      "an unknown body kind",
      (s: ReturnType<typeof fresh>) => (modOf(s, "recovery").body["kind"] = "partial"),
      "recovery",
      "body.kind",
    ],
    [
      "a blocked module's missing reason",
      (s: ReturnType<typeof fresh>) => delete modOf(s, "recovery").body["reason"],
      "recovery",
      "body.reason",
    ],
    [
      "a delivered state on a blocked body",
      (s: ReturnType<typeof fresh>) => (modOf(s, "recovery")["state"] = "Delivered"),
      "recovery",
      "state",
    ],
    [
      "a blocked state on a delivered body",
      (s: ReturnType<typeof fresh>) => (modOf(s, "capital-structure")["state"] = "Not assessable"),
      "capital-structure",
      "state",
    ],
    [
      "a state outside the Module state set",
      (s: ReturnType<typeof fresh>) => (modOf(s, "forecast")["state"] = "Done"),
      "forecast",
      "state",
    ],
    [
      "a contrary passage without text",
      (s: ReturnType<typeof fresh>) =>
        delete (modOf(s, "business-profile").body["contrary"] as Json)["text"],
      "business-profile",
      "body.contrary.text",
    ],
    [
      "a change view with an unknown trace",
      (s: ReturnType<typeof fresh>) =>
        ((modOf(s, "business-profile").body["changeView"] as Json)["trace"] = "nothing"),
      "business-profile",
      "body.changeView.trace",
    ],
    [
      "an unknown record kind",
      (s: ReturnType<typeof fresh>) =>
        (modOf(s, "business-profile").body.records[0] = { kind: "heat" }),
      "business-profile",
      "body.records[0].kind",
    ],
    [
      "a matrix with an empty-string note",
      (s: ReturnType<typeof fresh>) => (matrix(s)["note"] = ""),
      "business-profile",
      "body.records[0].note",
    ],
    [
      "a matrix with no rows",
      (s: ReturnType<typeof fresh>) => (matrix(s)["rows"] = []),
      "business-profile",
      "body.records[0].rows",
    ],
    [
      "a matrix with an empty-string grade",
      (s: ReturnType<typeof fresh>) => (matrixRow(s, 0)["probability"] = ""),
      "business-profile",
      "body.records[0].rows[0].probability",
    ],
    [
      "a matrix grade that is not text",
      (s: ReturnType<typeof fresh>) => (matrixRow(s, 3)["impact"] = 2),
      "business-profile",
      "body.records[0].rows[3].impact",
    ],
    [
      "a matrix with a missing grade field",
      (s: ReturnType<typeof fresh>) => delete matrixRow(s, 4)["impact"],
      "business-profile",
      "body.records[0].rows[4].impact",
    ],
    [
      "a matrix with two columns",
      (s: ReturnType<typeof fresh>) => (matrix(s)["columns"] = ["Risk", "Impact"]),
      "business-profile",
      "body.records[0].columns",
    ],
    [
      "a matrix with an empty column name",
      (s: ReturnType<typeof fresh>) => (matrix(s)["columns"] = ["Risk", "", "Impact"]),
      "business-profile",
      "body.records[0].columns[1]",
    ],
    [
      "a matrix risk row with an unknown trace",
      (s: ReturnType<typeof fresh>) => (matrixRow(s, 1)["trace"] = "nothing"),
      "business-profile",
      "body.records[0].rows[1].trace",
    ],
    [
      "a matrix with an unknown trace",
      (s: ReturnType<typeof fresh>) => (matrix(s)["trace"] = "nothing"),
      "business-profile",
      "body.records[0].trace",
    ],
    [
      "a matrix risk named twice",
      (s: ReturnType<typeof fresh>) => (matrixRow(s, 1)["risk"] = "Engine programme delay"),
      "business-profile",
      "body.records[0].rows[1].risk",
    ],
    [
      "a watch list with no items",
      (s: ReturnType<typeof fresh>) => (block(s, "watch")["items"] = []),
      "business-profile",
      "body.records[1].items",
    ],
    [
      "a watch timing that is not leading or lagging",
      (s: ReturnType<typeof fresh>) => (item(s, "watch", 0)["timing"] = "Leading"),
      "business-profile",
      "body.records[1].items[0].timing",
    ],
    [
      "a watch threshold that is blank",
      (s: ReturnType<typeof fresh>) => (item(s, "watch", 2)["threshold"] = ""),
      "business-profile",
      "body.records[1].items[2].threshold",
    ],
    [
      "a watch item with an unknown trace",
      (s: ReturnType<typeof fresh>) => (item(s, "watch", 1)["trace"] = "nothing"),
      "business-profile",
      "body.records[1].items[1].trace",
    ],
    [
      "a question with no items",
      (s: ReturnType<typeof fresh>) => (block(s, "questions")["items"] = []),
      "business-profile",
      "body.records[2].items",
    ],
    [
      "a question state outside the answer states",
      (s: ReturnType<typeof fresh>) => (item(s, "questions", 1)["state"] = "Open"),
      "business-profile",
      "body.records[2].items[1].state",
    ],
    [
      "an answered question with no answer",
      (s: ReturnType<typeof fresh>) => (item(s, "questions", 0)["answer"] = null),
      "business-profile",
      "body.records[2].items[0].answer",
    ],
    [
      "a not answered question that has an answer",
      (s: ReturnType<typeof fresh>) => (item(s, "questions", 2)["answer"] = "Some."),
      "business-profile",
      "body.records[2].items[2].answer",
    ],
    [
      "an empty-string answer",
      (s: ReturnType<typeof fresh>) => (item(s, "questions", 0)["answer"] = ""),
      "business-profile",
      "body.records[2].items[0].answer",
    ],
    [
      "a question with a trace and no answer",
      (s: ReturnType<typeof fresh>) => (item(s, "questions", 1)["trace"] = "bp-risk-1"),
      "business-profile",
      "body.records[2].items[1].trace",
    ],
    [
      "a pathway with no steps",
      (s: ReturnType<typeof fresh>) => (block(s, "edges")["steps"] = []),
      "business-profile",
      "body.records[3].steps",
    ],
    [
      "a pathway step with an empty line",
      (s: ReturnType<typeof fresh>) => (step(s, 1)["text"] = ""),
      "business-profile",
      "body.records[3].steps[1].text",
    ],
    [
      "a pathway step named twice",
      (s: ReturnType<typeof fresh>) => (step(s, 2)["title"] = "Ramp slips"),
      "business-profile",
      "body.records[3].steps[2].title",
    ],
    [
      "two blocks with one title",
      (s: ReturnType<typeof fresh>) => (block(s, "edges")["title"] = "Indicators to watch"),
      "business-profile",
      "body.records[3].title",
    ],
    [
      "a record that is not an object",
      (s: ReturnType<typeof fresh>) => (modOf(s, "business-profile").body.records[0] = "heat"),
      "business-profile",
      "body.records[0]",
    ],
    [
      "no findings",
      (s: ReturnType<typeof fresh>) =>
        ((modOf(s, "business-profile").body["findings"] as unknown[]).length = 0),
      "business-profile",
      "body.findings",
    ],
    [
      "no limitation items",
      (s: ReturnType<typeof fresh>) =>
        (((modOf(s, "business-profile").body["limitations"] as Json)["items"] as unknown[]).length =
          0),
      "business-profile",
      "body.limitations.items",
    ],
    [
      "a repeated module id",
      (s: ReturnType<typeof fresh>) =>
        (modOf(s, "industry-and-competition")["id"] = "business-profile"),
      "industry-and-competition",
      "id",
    ],
    [
      "a repeated module name",
      (s: ReturnType<typeof fresh>) =>
        (modOf(s, "industry-and-competition")["name"] = "Business profile"),
      "industry-and-competition",
      "name",
    ],
  ])("is invalid for %s, with its path", (_, break_, id, path) => {
    const slice = fresh();
    const where = at(slice, id);
    break_(slice);
    expect(invalidReason(slice)).toContain(`${where}.${path}`);
  });

  it("rejects a finished run with no modules and a loading run that carries them", () => {
    const missing = fresh();
    runOf(missing, 0).modules = null;
    expect(invalidReason(missing)).toContain("issuers[0].runs[0].modules");
    const loaded = fresh();
    runOf(loaded, 1).modules = runOf(fresh(), 0).modules;
    expect(invalidReason(loaded)).toContain("issuers[0].runs[1].modules");
  });

  it("rejects a module item, in the Overview or on the Changes page, whose module the run lacks", () => {
    const overview = fresh();
    (((runOf(overview, 0).overview["modules"] as Json)["items"] as Json[])[0] as Json)["module"] =
      "nowhere";
    expect(invalidReason(overview)).toContain(
      "issuers[0].runs[0].overview.modules.items[0].module",
    );
    const changes = fresh();
    (((runOf(changes, 0).changes["modules"] as Json)["items"] as Json[])[0] as Json)["module"] =
      "nowhere";
    expect(invalidReason(changes)).toContain("issuers[0].runs[0].changes.modules.items[0].module");
    const capped = fresh();
    const held = runOf(capped, 3).modules as Mod[];
    held.splice(
      held.findIndex((m) => m["id"] === "recovery"),
      1,
    );
    expect(invalidReason(capped)).toContain("issuers[0].runs[3].overview.modules.items[2].module");
  });

  it("rejects a collapsed item that names a module the run does not hold, or counts wrongly", () => {
    const overview = (slice: ReturnType<typeof fresh>, r: number) =>
      (runOf(slice, r).overview["modules"] as { items: Json[] }).items;
    const named = fresh();
    (overview(named, 2)[0] as Json)["lead"] = "Business profile, Treasury, Credit snapshot.";
    expect(invalidReason(named)).toContain("issuers[0].runs[2].overview.modules.items[0].lead");
    const dropped = fresh();
    (runOf(dropped, 3).modules as Mod[]).splice(0, 1);
    runOf(dropped, 3).head["firstModule"] = "industry-and-competition";
    expect(invalidReason(dropped)).toContain("issuers[0].runs[3].overview.modules.items[0].lead");
    const counted = fresh();
    (overview(counted, 3)[0] as Json)["title"] = "9 modules delivered";
    expect(invalidReason(counted)).toContain("issuers[0].runs[3].overview.modules.items[0].title");
    const changes = fresh();
    const item = (runOf(changes, 0).changes["modules"] as { items: Json[] }).items[
      (runOf(changes, 0).changes["modules"] as { items: Json[] }).items.findIndex(
        (i) => i["module"] === null,
      )
    ] as Json;
    item["lead"] = `${String(item["lead"])} Treasury.`;
    expect(invalidReason(changes)).toMatch(/runs\[0\]\.changes\.modules\.items\[\d+\]\.lead/);
  });

  it("rejects a first module the run does not hold", () => {
    const slice = fresh();
    runOf(slice, 0).head["firstModule"] = "nowhere";
    expect(invalidReason(slice)).toContain("issuers[0].runs[0].head.firstModule");
  });

  it("rejects no first module on a run that holds modules, and one on a run that loads", () => {
    const none = fresh();
    runOf(none, 0).head["firstModule"] = null;
    expect(invalidReason(none)).toContain("issuers[0].runs[0].head.firstModule");
    const loading = fresh();
    runOf(loading, 1).head["firstModule"] = "business-profile";
    expect(invalidReason(loading)).toContain("issuers[0].runs[1].head.firstModule");
  });

  it("allows no first module on a run that holds no modules", () => {
    const slice = fresh();
    const run = runOf(slice, 3);
    run.modules = [];
    run.head["firstModule"] = null;
    (run.overview["modules"] as { items: Json[] }).items = [
      { title: "Nothing", lead: "No module ran.", state: "Not run", module: null },
    ];
    expect(readSlice(slice).kind).toBe("ok");
    run.head["firstModule"] = "business-profile";
    expect(invalidReason(slice)).toContain("issuers[0].runs[3].head.firstModule");
  });
});

describe("readSlice, the data module's records", () => {
  type Mod = Json & { body: Json & { records: Json[] } };
  const mod = (slice: ReturnType<typeof fresh>): Mod => {
    const run = (slice.issuers[0]?.["runs"] as Json[])[0] as Json;
    const found = (run["modules"] as Mod[]).find((m) => m["id"] === "capital-structure");
    if (found === undefined) throw new Error("no capital structure");
    return found;
  };
  const records = (slice: ReturnType<typeof fresh>) => mod(slice).body.records;
  const blockOf = (slice: ReturnType<typeof fresh>, kind: string) =>
    records(slice).find((r) => r["kind"] === kind) as Json;
  const items = (slice: ReturnType<typeof fresh>, kind: string) =>
    blockOf(slice, kind)["items"] as Json[];
  const where = (slice: ReturnType<typeof fresh>, kind: string) =>
    `issuers[0].runs[0].modules[${String((slice.issuers[0]?.["runs"] as { modules: Json[] }[])[0]?.modules.findIndex((m) => m["id"] === "capital-structure"))}].body.records[${String(records(slice).findIndex((r) => r["kind"] === kind))}]`;

  it("reads the headline figures and measures as the mock words them", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error(result.kind);
    const body = result.data.issuers[0]?.runs[0]?.modules?.find(
      (m) => m.id === "capital-structure",
    )?.body;
    if (body?.kind !== "delivered") throw new Error("not delivered");
    const metrics = body.records.find((r) => r.kind === "metrics");
    const measures = body.records.find((r) => r.kind === "measures");
    expect(
      metrics?.kind === "metrics" && metrics.items.map((i) => [i.label, i.value, i.note]),
    ).toEqual([
      ["Gross debt", { kind: "value", text: "USD 2,398m", at: 2398 }, "At 30 Sep 2026"],
      ["Net debt", { kind: "value", text: "USD 2,236m", at: 2236 }, "After USD 162m cash"],
      ["Net leverage", { kind: "value", text: "4.6x", at: 4.6 }, "Net debt to EBITDA"],
      [
        "Secured leverage",
        { kind: "value", text: "3.3x", at: 3.3 },
        "First-lien net debt to EBITDA",
      ],
      [
        "Average cost of debt",
        { kind: "withheld", reason: null },
        "Marked confidential in the source",
      ],
      ["Next maturity", { kind: "value", text: "Mar 2028", at: null }, "USD 310m unsecured notes"],
    ]);
    expect(
      measures?.kind === "measures" &&
        measures.items.map((i) => [i.label, i.earlier === null, i.delta]),
    ).toEqual([
      ["Net leverage", false, { text: "Lower by 0.3x on 2025", direction: "down" }],
      ["Liquidity", false, { text: "Lower by USD 43m on June", direction: "down" }],
      ["Interest cover", true, null],
    ]);
  });

  const broken: [string, string, (b: Json) => unknown, string][] = [
    ["headline figures with no items", "metrics", (b: Json) => (b["items"] = []), "items"],
    [
      "a headline figure with an empty-string value",
      "metrics",
      (b: Json) =>
        (((b["items"] as Json[])[0] as Json)["value"] = { kind: "value", text: "", at: null }),
      "items[0].value.text",
    ],
    [
      "a headline figure with an unknown trace",
      "metrics",
      (b: Json) => (((b["items"] as Json[])[1] as Json)["trace"] = "nothing"),
      "items[1].trace",
    ],
    [
      "a headline figure named twice",
      "metrics",
      (b: Json) => (((b["items"] as Json[])[1] as Json)["label"] = "Gross debt"),
      "items[1].label",
    ],
    ["an empty-string navigator label", "metrics", (b: Json) => (b["nav"] = ""), "nav"],
    ["measures with no items", "measures", (b: Json) => (b["items"] = []), "items"],
    [
      "a measure with an empty-string earlier figure",
      "measures",
      (b: Json) =>
        (((b["items"] as Json[])[0] as Json)["earlier"] = { kind: "value", text: "", at: null }),
      "items[0].earlier.text",
    ],
    [
      "a measure with an unknown direction",
      "measures",
      (b: Json) =>
        ((((b["items"] as Json[])[0] as Json)["delta"] as Json)["direction"] = "sideways"),
      "items[0].delta.direction",
    ],
    [
      "a delta given beside a missing earlier period",
      "measures",
      (b: Json) =>
        (((b["items"] as Json[])[2] as Json)["delta"] = { text: "Higher", direction: "up" }),
      "items[2].delta",
    ],
    [
      "a delta given beside a withheld current figure",
      "measures",
      (b: Json) =>
        (((b["items"] as Json[])[0] as Json)["current"] = { kind: "withheld", reason: null }),
      "items[0].delta",
    ],
    [
      "a measure with a missing consequence",
      "measures",
      (b: Json) => delete ((b["items"] as Json[])[1] as Json)["consequence"],
      "items[1].consequence",
    ],
  ];
  it.each(broken)("is invalid for %s, with its path", (_, kind, break_, path) => {
    const slice = fresh();
    const base = where(slice, kind);
    break_(blockOf(slice, kind));
    expect(invalidReason(slice)).toContain(`${base}.${path}`);
  });

  it("accepts a measure with both periods as values and no delta, and counts the items read", () => {
    const slice = fresh();
    (items(slice, "measures")[0] as Json)["delta"] = null;
    expect(readSlice(slice).kind).toBe("ok");
  });
});
