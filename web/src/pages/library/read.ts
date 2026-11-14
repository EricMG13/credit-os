import { STATUS_SETS } from "@/components/status/sets";
import type { SliceResult } from "../route-table";
import type {
  BottomLineText,
  Cell,
  Change,
  ChangeModuleItem,
  ChangeState,
  Changes,
  ChangeView,
  DateState,
  DatedItem,
  Finding,
  HomeCard,
  History,
  HistoryEntry,
  Issuer,
  IssuerCard,
  LibraryHome,
  LibrarySlice,
  Limitations,
  Measure,
  ModuleItem,
  ModuleState,
  MeasureKey,
  MeasureSpec,
  Metric,
  Overview,
  Point,
  Run,
  RunHead,
  RunState,
  Trace,
  TreeNode,
} from "./slice";
import { APPLIED_LABELS } from "./slice";

type Rec = Record<string, unknown>;

/** A malformed record: `path` is the first failing path, for example `home.cards[1].note`. */
class SliceError extends Error {
  constructor(path: string, expected: string) {
    super(`${path}: expected ${expected}`);
  }
}

const child = (path: string, key: string): string => (path === "" ? key : `${path}.${key}`);
const nth = (path: string, index: number): string => `${path}[${String(index)}]`;

/** The object at `path`; arrays, null and other types fail. */
function rec(value: unknown, path: string): Rec {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new SliceError(path, "an object");
  }
  return value as Rec;
}

/** A field read only from the object's own properties, so a prototype member is never a field. */
function own(o: Rec, key: string): unknown {
  return Object.hasOwn(o, key) ? o[key] : undefined;
}

function str(o: Rec, key: string, path: string): string {
  const value = own(o, key);
  if (typeof value !== "string") throw new SliceError(child(path, key), "a string");
  return value;
}

/** A string or an explicit `null`; an absent field is not missing, it is malformed. */
function strOrNull(o: Rec, key: string, path: string): string | null {
  const value = own(o, key);
  if (value !== null && typeof value !== "string") {
    throw new SliceError(child(path, key), "a string or null");
  }
  return value;
}

function num(o: Rec, key: string, path: string): number {
  const value = own(o, key);
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new SliceError(child(path, key), "a finite number");
  }
  return value;
}

function numOrNull(o: Rec, key: string, path: string): number | null {
  return own(o, key) === null ? null : num(o, key, path);
}

function oneOf<T extends string>(o: Rec, key: string, path: string, allowed: readonly T[]): T {
  const value = own(o, key);
  const found = allowed.find((word) => word === value);
  if (found === undefined) throw new SliceError(child(path, key), `one of ${allowed.join(", ")}`);
  return found;
}

function list<T>(
  o: Rec,
  key: string,
  path: string,
  read: (item: unknown, itemPath: string) => T,
): T[] {
  const value = own(o, key);
  if (!Array.isArray(value)) throw new SliceError(child(path, key), "a list");
  return (value as unknown[]).map((item, index) => read(item, nth(child(path, key), index)));
}

function strings(o: Rec, key: string, path: string): string[] {
  return list(o, key, path, (item, itemPath) => {
    if (typeof item !== "string") throw new SliceError(itemPath, "a string");
    return item;
  });
}

export function cell(o: Rec, key: string, path: string): Cell {
  const at = child(path, key);
  const value = own(o, key);
  if (value === null) return null;
  const c = rec(value, at);
  switch (oneOf(c, "kind", at, ["value", "withheld", "gap"])) {
    case "value":
      return { kind: "value", text: str(c, "text", at), at: numOrNull(c, "at", at) };
    case "withheld":
      return { kind: "withheld", reason: strOrNull(c, "reason", at) };
    case "gap":
      return { kind: "gap", reason: str(c, "reason", at) };
  }
}

const RUN_STATES = Object.keys(STATUS_SETS["Run states"]) as RunState[];

function readProgress(value: unknown, path: string): IssuerCard["progress"] {
  const p = rec(value, path);
  const progress = {
    text: str(p, "text", path),
    value: num(p, "value", path),
    max: num(p, "max", path),
  };
  if (!(progress.max > 0)) throw new SliceError(child(path, "max"), "a number above 0");
  if (progress.value < 0 || progress.value > progress.max) {
    throw new SliceError(child(path, "value"), "a number from 0 to max");
  }
  return progress;
}

function readMeasure(o: Rec, key: string, path: string): Measure {
  const at = child(path, key);
  const value = own(o, key);
  if (value === null) return null;
  const m = rec(value, at);
  return {
    text: str(m, "text", at),
    at: num(m, "at", at),
    basis: oneOf(m, "basis", at, ["reported", "adjusted"]),
    description: str(m, "description", at),
  };
}

/** One value for each measure, read by `read` at `path.<measure>`. */
function eachMeasure<T>(
  o: Rec,
  key: string,
  path: string,
  read: (m: Rec, k: MeasureKey, p: string) => T,
): Record<MeasureKey, T> {
  const at = child(path, key);
  const m = rec(own(o, key), at);
  return {
    leverage: read(m, "leverage", at),
    netLeverage: read(m, "netLeverage", at),
    interestCoverage: read(m, "interestCoverage", at),
  };
}

function readSpec(o: Rec, key: MeasureKey, path: string): MeasureSpec {
  const at = child(path, key);
  const m = rec(own(o, key), at);
  const labels = new Set<string>();
  return {
    name: str(m, "name", at),
    countLine: str(m, "countLine", at),
    bands: list(m, "bands", at, (item, itemPath) => {
      const b = rec(item, itemPath);
      const min = numOrNull(b, "min", itemPath);
      const max = numOrNull(b, "max", itemPath);
      if (min !== null && max !== null && min >= max) {
        throw new SliceError(child(itemPath, "max"), "a number above min");
      }
      const label = str(b, "label", itemPath);
      if (labels.has(label))
        throw new SliceError(child(itemPath, "label"), "a label not used by an earlier band");
      labels.add(label);
      return { label, min, max };
    }),
  };
}

function readCard(value: unknown, path: string, issuerIds: ReadonlySet<string>): HomeCard {
  const c = rec(value, path);
  if (oneOf(c, "kind", path, ["issuer", "loading"]) === "loading") return { kind: "loading" };
  const issuer = str(c, "issuer", path);
  if (!issuerIds.has(issuer)) throw new SliceError(child(path, "issuer"), "an id in issuers");
  return {
    kind: "issuer",
    issuer,
    name: str(c, "name", path),
    sector: str(c, "sector", path),
    state: oneOf(c, "state", path, RUN_STATES),
    lead: str(c, "lead", path),
    note: strOrNull(c, "note", path),
    asOf: str(c, "asOf", path),
    pathway: str(c, "pathway", path),
    progress: readProgress(own(c, "progress"), child(path, "progress")),
    href: strOrNull(c, "href", path),
    measures: eachMeasure(c, "measures", path, readMeasure),
  };
}

function readHome(value: unknown, path: string, issuerIds: ReadonlySet<string>): LibraryHome {
  const h = rec(value, path);
  const filtersPath = child(path, "filters");
  const f = rec(own(h, "filters"), filtersPath);
  const appliedLabels = strings(f, "appliedLabels", filtersPath);
  if (appliedLabels.length !== APPLIED_LABELS) {
    throw new SliceError(child(filtersPath, "appliedLabels"), `${String(APPLIED_LABELS)} labels`);
  }
  return {
    subtitle: str(h, "subtitle", path),
    filters: {
      sector: strings(f, "sector", filtersPath),
      pathway: strings(f, "pathway", filtersPath),
      state: strings(f, "state", filtersPath),
      appliedLabels,
    },
    cards: list(h, "cards", path, (card, cardPath) => readCard(card, cardPath, issuerIds)),
    list: {
      measures: eachMeasure(
        rec(own(h, "list"), child(path, "list")),
        "measures",
        child(path, "list"),
        readSpec,
      ),
    },
  };
}

function readEntry(value: unknown, path: string): HistoryEntry {
  const e = rec(value, path);
  const changesValue = own(e, "changes");
  const changesPath = child(path, "changes");
  const changes =
    changesValue === null
      ? null
      : {
          label: str(rec(changesValue, changesPath), "label", changesPath),
          run: str(rec(changesValue, changesPath), "run", changesPath),
        };
  const state = oneOf(e, "state", path, RUN_STATES);
  const report = strOrNull(e, "report", path);
  // Nothing from a run that did not finish is shown: only Finished and Capped can be read.
  if (state !== "Finished" && state !== "Capped") {
    if (report !== null) throw new SliceError(child(path, "report"), `null for a ${state} run`);
    if (changes !== null) throw new SliceError(changesPath, `null for a ${state} run`);
  }
  return {
    asOf: str(e, "asOf", path),
    ran: str(e, "ran", path),
    state,
    pathway: str(e, "pathway", path),
    text: str(e, "text", path),
    report,
    changes,
  };
}

function readHistory(value: unknown, path: string): History {
  const h = rec(value, path);
  const latest = strOrNull(h, "latest", path);
  const empty = strOrNull(h, "empty", path);
  const entries = list(h, "entries", path, readEntry);
  const seen = new Set<string>();
  for (const [index, entry] of entries.entries()) {
    const key = JSON.stringify([entry.asOf, entry.ran]);
    if (seen.has(key)) {
      throw new SliceError(
        nth(child(path, "entries"), index),
        "an asOf and ran not used by an earlier entry",
      );
    }
    seen.add(key);
  }
  if (latest === null && empty === null) {
    throw new SliceError(child(path, "empty"), "a sentence when there is no latest run");
  }
  if (latest !== null && empty !== null) {
    throw new SliceError(child(path, "empty"), "null when there is a latest run");
  }
  if (latest !== null && !entries.some((entry) => entry.report === latest)) {
    throw new SliceError(child(path, "latest"), "a run an entry's report opens");
  }
  return { subtitle: str(h, "subtitle", path), latest, empty, entries };
}

function readTree(value: unknown, path: string): TreeNode {
  const n = rec(value, path);
  return {
    label: str(n, "label", path),
    value: strOrNull(n, "value", path),
    note: strOrNull(n, "note", path),
    children: list(n, "children", path, readTree),
  };
}

function readExcerpt(t: Rec, path: string): Trace["excerpt"] {
  const at = child(path, "excerpt");
  const value = own(t, "excerpt");
  if (value === null) return null;
  const e = rec(value, at);
  return { quote: str(e, "quote", at), source: str(e, "source", at) };
}

function readTrace(value: unknown, path: string): Trace {
  const t = rec(value, path);
  return {
    title: str(t, "title", path),
    heading: str(t, "heading", path),
    subtitle: str(t, "subtitle", path),
    statement: str(t, "statement", path),
    derivation: readTree(own(t, "derivation"), child(path, "derivation")),
    excerpt: readExcerpt(t, path),
    qualification: strOrNull(t, "qualification", path),
    evidenceItem: str(t, "evidenceItem", path),
  };
}

function readHead(value: unknown, path: string): RunHead {
  const h = rec(value, path);
  const tabsPath = child(path, "tabs");
  return {
    issuerName: str(h, "issuerName", path),
    asOf: str(h, "asOf", path),
    pathway: str(h, "pathway", path),
    state: oneOf(h, "state", path, RUN_STATES),
    tabs: { modulesCount: str(rec(own(h, "tabs"), tabsPath), "modulesCount", tabsPath) },
    firstModule: strOrNull(h, "firstModule", path),
    forecastHref: strOrNull(h, "forecastHref", path),
  };
}

/** A trace key is checked against the run's own traces, so it is read after them. */
type Traces = Readonly<Record<string, Trace>>;

function readMetric(value: unknown, path: string, traces: Traces): Metric {
  const m = rec(value, path);
  return {
    label: str(m, "label", path),
    value: cell(m, "value", path),
    note: str(m, "note", path),
    trace: traceKey(m, "trace", path, traces),
  };
}

function readPoint(value: unknown, path: string, traces: Traces): Point {
  const p = rec(value, path);
  return {
    figure: cell(p, "figure", path),
    text: str(p, "text", path),
    qualifier: str(p, "qualifier", path),
    trace: traceKey(p, "trace", path, traces),
  };
}

function readBottomLine(value: unknown, path: string, traces: Traces): BottomLineText {
  const b = rec(value, path);
  return {
    label: str(b, "label", path),
    lead: str(b, "lead", path),
    rest: str(b, "rest", path),
    trace: traceKey(b, "trace", path, traces),
  };
}

/** The same list, each item's `key` unused by an earlier one; the failing path ends in `field`. */
function unique<T>(items: T[], path: string, key: (item: T) => string, field: string): T[] {
  const seen = new Set<string>();
  for (const [index, item] of items.entries()) {
    if (seen.has(key(item))) {
      throw new SliceError(child(nth(path, index), field), `a ${field} not used by an earlier one`);
    }
    seen.add(key(item));
  }
  return items;
}

/** A list the page draws as a section: an empty one would draw a heading over nothing. */
function some<T>(items: T[], path: string): T[] {
  if (items.length === 0) throw new SliceError(path, "at least one item");
  return items;
}

/** For and against has two columns, "supports" and "against", each with its own points. */
function readColumns(sides: Rec, path: string, traces: Traces): Overview["sides"]["columns"] {
  const columns = list(sides, "columns", path, (column, columnPath) => {
    const c = rec(column, columnPath);
    return {
      name: str(c, "name", columnPath),
      items: some(
        unique(
          list(c, "items", columnPath, (item, p) => readPoint(item, p, traces)),
          child(columnPath, "items"),
          (point) => point.text,
          "text",
        ),
        child(columnPath, "items"),
      ),
    };
  });
  if (columns.length !== 2) throw new SliceError(child(path, "columns"), "two columns");
  return columns;
}

function readFinding(value: unknown, path: string, traces: Traces): Finding {
  const f = rec(value, path);
  return {
    number: str(f, "number", path),
    lead: str(f, "lead", path),
    body: str(f, "body", path),
    trace: traceKey(f, "trace", path, traces),
  };
}

function readChangeView(value: unknown, path: string, traces: Traces): ChangeView {
  const c = rec(value, path);
  return {
    title: str(c, "title", path),
    text: str(c, "text", path),
    trace: traceKey(c, "trace", path, traces),
  };
}

const DATE_STATES = Object.keys(STATUS_SETS["Dated records"]) as DateState[];

function readDate(value: unknown, path: string): DatedItem {
  const d = rec(value, path);
  return {
    date: str(d, "date", path),
    state: oneOf(d, "state", path, DATE_STATES),
    title: str(d, "title", path),
    text: str(d, "text", path),
  };
}

const MODULE_STATES = Object.keys(STATUS_SETS["Module state"]) as ModuleState[];

function readModuleItem(value: unknown, path: string): ModuleItem {
  const m = rec(value, path);
  return {
    title: str(m, "title", path),
    lead: str(m, "lead", path),
    state: oneOf(m, "state", path, MODULE_STATES),
    module: strOrNull(m, "module", path),
  };
}

function readLimitations(value: unknown, path: string, traces: Traces): Limitations {
  const l = rec(value, path);
  const linkPath = child(path, "gapsLink");
  return {
    count: str(l, "count", path),
    gapsLink: { label: str(rec(own(l, "gapsLink"), linkPath), "label", linkPath) },
    items: some(
      unique(
        list(l, "items", path, (item, p) => {
          const i = rec(item, p);
          return { text: str(i, "text", p), trace: traceKey(i, "trace", p, traces) };
        }),
        child(path, "items"),
        (item) => item.text,
        "text",
      ),
      child(path, "items"),
    ),
  };
}

function readModules(value: unknown, path: string): Overview["modules"] {
  const m = rec(value, path);
  return {
    summary: str(m, "summary", path),
    items: some(
      unique(
        list(m, "items", path, readModuleItem),
        child(path, "items"),
        (item) => item.title,
        "title",
      ),
      child(path, "items"),
    ),
  };
}

function readOverview(value: unknown, path: string, traces: Traces): Overview {
  const o = rec(value, path);
  const sidesPath = child(path, "sides");
  const sides = rec(own(o, "sides"), sidesPath);
  return {
    bottomLine: readBottomLine(own(o, "bottomLine"), child(path, "bottomLine"), traces),
    metricsLabel: str(o, "metricsLabel", path),
    metrics: unique(
      list(o, "metrics", path, (m, p) => readMetric(m, p, traces)),
      child(path, "metrics"),
      (m) => m.label,
      "label",
    ),
    sides: {
      heading: str(sides, "heading", sidesPath),
      note: str(sides, "note", sidesPath),
      columns: readColumns(sides, sidesPath, traces),
    },
    findings: some(
      unique(
        list(o, "findings", path, (f, p) => readFinding(f, p, traces)),
        child(path, "findings"),
        (f) => f.number,
        "number",
      ),
      child(path, "findings"),
    ),
    changeView: readChangeView(own(o, "changeView"), child(path, "changeView"), traces),
    dates: some(
      unique(
        list(o, "dates", path, readDate),
        child(path, "dates"),
        (d) => `${d.date}|${d.title}`,
        "title",
      ),
      child(path, "dates"),
    ),
    modules: readModules(own(o, "modules"), child(path, "modules")),
    limitations: readLimitations(own(o, "limitations"), child(path, "limitations"), traces),
  };
}

const CHANGE_STATES = Object.keys(STATUS_SETS["Change state"]) as ChangeState[];

/** A figure of a change; the Table side draws it as the exact string, so a blank one is rejected. */
function changeCell(o: Rec, key: string, path: string): Cell {
  const c = cell(o, key, path);
  if (c !== null && c.kind === "value" && c.text === "") {
    throw new SliceError(child(child(path, key), "text"), "a non-empty string");
  }
  return c;
}

/** Both figures of a change are values: only then can a direction mark or its words be delivered. */
const isValue = (c: Cell): boolean => c !== null && c.kind === "value";

function readChange(value: unknown, path: string, traces: Traces): Change {
  const c = rec(value, path);
  const from = changeCell(c, "from", path);
  const current = changeCell(c, "current", path);
  const direction = oneOf(c, "direction", path, ["up", "down", "flat", "none"]);
  const change = strOrNull(c, "change", path);
  if (change === "") throw new SliceError(child(path, "change"), "a non-empty string or null");
  if (!isValue(from) || !isValue(current)) {
    if (direction !== "none") {
      throw new SliceError(child(path, "direction"), "none unless both figures are values");
    }
    if (change !== null) {
      throw new SliceError(child(path, "change"), "null unless both figures are values");
    }
  }
  if (direction !== "none" && change === null) {
    throw new SliceError(child(path, "change"), "the delivered words for a direction mark");
  }
  return {
    measure: str(c, "measure", path),
    kind: str(c, "kind", path),
    current,
    from,
    direction,
    change,
    cause: str(c, "cause", path),
    effect: str(c, "effect", path),
    trace: traceKey(c, "trace", path, traces),
  };
}

function readChangeModule(value: unknown, path: string): ChangeModuleItem {
  const m = rec(value, path);
  return {
    title: str(m, "title", path),
    lead: str(m, "lead", path),
    state: oneOf(m, "state", path, CHANGE_STATES),
    module: strOrNull(m, "module", path),
  };
}

function readChanges(value: unknown, path: string, traces: Traces): Changes {
  const c = rec(value, path);
  if (oneOf(c, "kind", path, ["none", "compared"]) === "none") {
    return { kind: "none", title: str(c, "title", path), text: str(c, "text", path) };
  }
  const changesPath = child(path, "changes");
  const changes = unique(
    list(c, "changes", path, (item, p) => readChange(item, p, traces)),
    changesPath,
    (item) => item.measure,
    "measure",
  );
  if (changes.length === 0) throw new SliceError(changesPath, "at least one change");
  const modulesPath = child(path, "modules");
  const m = rec(own(c, "modules"), modulesPath);
  return {
    kind: "compared",
    heading: str(c, "heading", path),
    subtitle: str(c, "subtitle", path),
    earlierLabel: str(c, "earlierLabel", path),
    currentLabel: str(c, "currentLabel", path),
    tableNote: str(c, "tableNote", path),
    changes,
    modules: {
      summary: str(m, "summary", modulesPath),
      items: unique(
        list(m, "items", modulesPath, readChangeModule),
        child(modulesPath, "items"),
        (item) => item.title,
        "title",
      ),
    },
  };
}

function readRun(value: unknown, path: string): Run {
  const r = rec(value, path);
  const tracesPath = child(path, "traces");
  const traces = rec(own(r, "traces"), tracesPath);
  const loading = own(r, "loading");
  if (typeof loading !== "boolean") throw new SliceError(child(path, "loading"), "a boolean");
  const base = {
    id: str(r, "id", path),
    head: readHead(own(r, "head"), child(path, "head")),
    traces: Object.fromEntries(
      Object.keys(traces).map((key) => [key, readTrace(traces[key], child(tracesPath, key))]),
    ),
  };
  const overviewPath = child(path, "overview");
  const changesPath = child(path, "changes");
  if (loading) {
    if (own(r, "overview") !== null) throw new SliceError(overviewPath, "null for a loading run");
    if (own(r, "changes") !== null) throw new SliceError(changesPath, "null for a loading run");
    return { ...base, loading, overview: null, changes: null };
  }
  return {
    ...base,
    loading,
    overview: readOverview(own(r, "overview"), overviewPath, base.traces),
    changes: readChanges(own(r, "changes"), changesPath, base.traces),
  };
}

function readRuns(i: Rec, path: string): Run[] {
  const runs = list(i, "runs", path, readRun);
  const seen = new Set<string>();
  for (const [index, run] of runs.entries()) {
    if (seen.has(run.id)) {
      throw new SliceError(
        child(nth(child(path, "runs"), index), "id"),
        "an id not used by an earlier run",
      );
    }
    seen.add(run.id);
  }
  return runs;
}

/**
 * The trace key an item carries: `null` for no trace, else a key of its run's `traces`. Pages read
 * their items' `trace` field through this, so a control never points at a trace the run lacks.
 */
export function traceKey(
  o: Rec,
  key: string,
  path: string,
  traces: Readonly<Record<string, Trace>>,
): string | null {
  const value = strOrNull(o, key, path);
  if (value !== null && !Object.hasOwn(traces, value)) {
    throw new SliceError(child(path, key), "a key of the run's traces");
  }
  return value;
}

function readIssuer(value: unknown, path: string): Issuer {
  const i = rec(value, path);
  return {
    id: str(i, "id", path),
    name: str(i, "name", path),
    history: readHistory(own(i, "history"), child(path, "history")),
    runs: readRuns(i, path),
  };
}

/** The library slice, or `absent` when the data file has none, or `invalid` naming the first failing path. */
export function readSlice(source: unknown): SliceResult<LibrarySlice> {
  if (source === undefined) return { kind: "absent" };
  try {
    const s = rec(source, "slice");
    const issuers = list(s, "issuers", "", readIssuer);
    const ids = new Set(issuers.map((issuer) => issuer.id));
    return { kind: "ok", data: { home: readHome(own(s, "home"), "home", ids), issuers } };
  } catch (error) {
    if (error instanceof SliceError) return { kind: "invalid", reason: error.message };
    throw error;
  }
}
