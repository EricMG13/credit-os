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
