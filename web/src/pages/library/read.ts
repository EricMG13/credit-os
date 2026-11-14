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
  BlockedBody,
  AnswerState,
  DateState,
  DeliveredBody,
  Download,
  Evidence,
  FileState,
  GapForm,
  GapRow,
  GapSeverity,
  GapTable,
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
  Module,
  Overview,
  Point,
  RecordBlock,
  Reader,
  Run,
  RunHead,
  RunState,
  SourceFile,
  Trace,
  TestState,
  TraceRow,
  TraceTable,
  TreeNode,
} from "./slice";
import { APPLIED_LABELS, CHART_TABLE_LIMITS } from "./slice";

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

/** The figure at `at`: `null` is missing, otherwise a value, a withheld figure or a gap. */
function cellOf(value: unknown, at: string): Cell {
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

export function cell(o: Rec, key: string, path: string): Cell {
  return cellOf(own(o, key), child(path, key));
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

/** A figure a page draws as written: a blank text would draw nothing and the tables refuse it. */
function shownOf(value: unknown, at: string): Cell {
  const c = cellOf(value, at);
  if (c !== null && c.kind === "value" && c.text === "") {
    throw new SliceError(child(at, "text"), "a non-empty string");
  }
  return c;
}

const shownCell = (o: Rec, key: string, path: string): Cell =>
  shownOf(own(o, key), child(path, key));

/** A trace key is checked against the run's own traces, so it is read after them. */
type Traces = Readonly<Record<string, Trace>>;

function readMetric(value: unknown, path: string, traces: Traces): Metric {
  const m = rec(value, path);
  return {
    label: str(m, "label", path),
    value: shownCell(m, "value", path),
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

/** Both figures of a change are values: only then can a direction mark or its words be delivered. */
const isValue = (c: Cell): boolean => c !== null && c.kind === "value";

function readChange(value: unknown, path: string, traces: Traces): Change {
  const c = rec(value, path);
  const from = shownCell(c, "from", path);
  const current = shownCell(c, "current", path);
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

const DELIVERED_STATES: ModuleState[] = ["Delivered", "Delivered with gaps"];
const BLOCKED_STATES: ModuleState[] = ["Not assessable", "Not run"];

/** A passage with a title that the module may not have: absent is an explicit `null`. */
function optionalView(o: Rec, key: string, path: string, traces: Traces): ChangeView | null {
  return own(o, key) === null ? null : readChangeView(own(o, key), child(path, key), traces);
}

/** Text a table draws as given: the table refuses a blank one, so it is `null` or has a character. */
function gradeOrNull(o: Rec, key: string, path: string): string | null {
  const value = strOrNull(o, key, path);
  if (value === "") throw new SliceError(child(path, key), "a non-empty string or null");
  return value;
}

/** A name the table or list draws as a heading or label: never blank. */
function named(o: Rec, key: string, path: string): string {
  const value = str(o, key, path);
  if (value === "") throw new SliceError(child(path, key), "a non-empty string");
  return value;
}

function readMatrix(m: Rec, path: string, traces: Traces): RecordBlock {
  const columnsPath = child(path, "columns");
  const columns = list(m, "columns", path, (item, p) => {
    if (typeof item !== "string" || item === "") throw new SliceError(p, "a non-empty string");
    return item;
  });
  if (columns.length !== 3) throw new SliceError(columnsPath, "three columns");
  const rowsPath = child(path, "rows");
  const rows = some(
    unique(
      list(m, "rows", path, (item, p) => {
        const r = rec(item, p);
        return {
          risk: named(r, "risk", p),
          probability: gradeOrNull(r, "probability", p),
          impact: gradeOrNull(r, "impact", p),
          trace: traceKey(r, "trace", p, traces),
        };
      }),
      rowsPath,
      (row) => row.risk,
      "risk",
    ),
    rowsPath,
  );
  return {
    kind: "matrix",
    title: named(m, "title", path),
    note: gradeOrNull(m, "note", path),
    columns,
    rows,
    trace: traceKey(m, "trace", path, traces),
  };
}

function readWatch(w: Rec, path: string, traces: Traces): RecordBlock {
  const itemsPath = child(path, "items");
  return {
    kind: "watch",
    title: named(w, "title", path),
    items: some(
      unique(
        list(w, "items", path, (item, p) => {
          const i = rec(item, p);
          return {
            indicator: named(i, "indicator", p),
            threshold: named(i, "threshold", p),
            timing: oneOf(i, "timing", p, ["leading", "lagging"]),
            trace: traceKey(i, "trace", p, traces),
          };
        }),
        itemsPath,
        (item) => item.indicator,
        "indicator",
      ),
      itemsPath,
    ),
  };
}

const ANSWER_STATES = Object.keys(STATUS_SETS["Answer state"]) as AnswerState[];

/** A question has an answer unless it is "Not answered", and only an answer has sources. */
function readQuestion(item: unknown, path: string, traces: Traces) {
  const q = rec(item, path);
  const state = oneOf(q, "state", path, ANSWER_STATES);
  const answer = gradeOrNull(q, "answer", path);
  if (state === "Answered" && answer === null) {
    throw new SliceError(child(path, "answer"), "an answer for an Answered question");
  }
  if (state === "Not answered" && answer !== null) {
    throw new SliceError(child(path, "answer"), "null for a Not answered question");
  }
  const trace = traceKey(q, "trace", path, traces);
  if (answer === null && trace !== null) {
    throw new SliceError(child(path, "trace"), "null for a question with no answer");
  }
  return { question: named(q, "question", path), state, answer, trace };
}

function readQuestions(q: Rec, path: string, traces: Traces): RecordBlock {
  const itemsPath = child(path, "items");
  return {
    kind: "questions",
    title: named(q, "title", path),
    items: some(
      unique(
        list(q, "items", path, (item, p) => readQuestion(item, p, traces)),
        itemsPath,
        (item) => item.question,
        "question",
      ),
      itemsPath,
    ),
  };
}

function readEdges(e: Rec, path: string): RecordBlock {
  const stepsPath = child(path, "steps");
  return {
    kind: "edges",
    title: named(e, "title", path),
    steps: some(
      unique(
        list(e, "steps", path, (item, p) => {
          const step = rec(item, p);
          return { title: named(step, "title", p), text: named(step, "text", p) };
        }),
        stepsPath,
        (step) => step.title,
        "title",
      ),
      stepsPath,
    ),
  };
}

/** The label of the navigator entry a data block belongs to: text, or `null` for none. */
const navLabel = gradeOrNull;

function readMetrics(m: Rec, path: string, traces: Traces): RecordBlock {
  const itemsPath = child(path, "items");
  return {
    kind: "metrics",
    nav: navLabel(m, "nav", path),
    title: named(m, "title", path),
    items: some(
      unique(
        list(m, "items", path, (item, p) => readMetric(item, p, traces)),
        itemsPath,
        (item) => item.label,
        "label",
      ),
      itemsPath,
    ),
  };
}

function readDelta(o: Rec, path: string, held: boolean, earlier: Cell) {
  const at = child(path, "delta");
  if (own(o, "delta") === null) {
    // The page words a measure with no delta as "Earlier period n.a.": only that case may carry none.
    if (held) throw new SliceError(at, "a change, since both periods are values");
    if (earlier !== null)
      throw new SliceError(at, "a change, unless the earlier period is missing");
    return null;
  }
  if (!held) throw new SliceError(at, "null unless both periods are values");
  const d = rec(own(o, "delta"), at);
  return {
    text: named(d, "text", at),
    direction: oneOf(d, "direction", at, ["up", "down", "flat"]),
  };
}

function readStat(item: unknown, path: string, traces: Traces) {
  const m = rec(item, path);
  const current = shownCell(m, "current", path);
  const earlier = shownCell(m, "earlier", path);
  return {
    label: named(m, "label", path),
    current,
    earlier,
    delta: readDelta(m, path, isValue(current) && isValue(earlier), earlier),
    consequence: named(m, "consequence", path),
    trace: traceKey(m, "trace", path, traces),
  };
}

function readMeasures(m: Rec, path: string, traces: Traces): RecordBlock {
  const itemsPath = child(path, "items");
  return {
    kind: "measures",
    nav: navLabel(m, "nav", path),
    title: named(m, "title", path),
    items: some(
      unique(
        list(m, "items", path, (item, p) => readStat(item, p, traces)),
        itemsPath,
        (item) => item.label,
        "label",
      ),
      itemsPath,
    ),
  };
}

function readFact(item: unknown, path: string, traces: Traces) {
  const f = rec(item, path);
  return {
    label: named(f, "label", path),
    value: shownCell(f, "value", path),
    trace: traceKey(f, "trace", path, traces),
  };
}

function readFactGroup(value: unknown, path: string, traces: Traces) {
  const g = rec(value, path);
  const rowsPath = child(path, "rows");
  return {
    name: gradeOrNull(g, "name", path),
    rows: some(
      unique(
        list(g, "rows", path, (item, p) => readFact(item, p, traces)),
        rowsPath,
        (row) => row.label,
        "label",
      ),
      rowsPath,
    ),
  };
}

function readFacts(f: Rec, path: string, traces: Traces): RecordBlock {
  const groupsPath = child(path, "groups");
  return {
    kind: "facts",
    nav: navLabel(f, "nav", path),
    title: named(f, "title", path),
    groups: some(
      unique(
        list(f, "groups", path, (item, p) => readFactGroup(item, p, traces)),
        groupsPath,
        (group) => group.name ?? "",
        "name",
      ),
      groupsPath,
    ),
  };
}

const TEST_STATES = Object.keys(STATUS_SETS["Met or not met"]) as TestState[];

function readTest(item: unknown, path: string, traces: Traces) {
  const t = rec(item, path);
  return {
    text: named(t, "text", path),
    note: gradeOrNull(t, "note", path),
    value: shownCell(t, "value", path),
    trace: traceKey(t, "trace", path, traces),
  };
}

function readTestGroup(value: unknown, path: string, traces: Traces) {
  const g = rec(value, path);
  const itemsPath = child(path, "items");
  return {
    state: oneOf(g, "state", path, TEST_STATES),
    count: named(g, "count", path),
    items: some(
      unique(
        list(g, "items", path, (item, p) => readTest(item, p, traces)),
        itemsPath,
        (item) => item.text,
        "text",
      ),
      itemsPath,
    ),
  };
}

function readStatus(s: Rec, path: string, traces: Traces): RecordBlock {
  const groupsPath = child(path, "groups");
  return {
    kind: "status",
    nav: navLabel(s, "nav", path),
    title: named(s, "title", path),
    groups: some(
      unique(
        list(s, "groups", path, (item, p) => readTestGroup(item, p, traces)),
        groupsPath,
        (group) => group.state,
        "state",
      ),
      groupsPath,
    ),
  };
}

function bool(o: Rec, key: string, path: string): boolean {
  const value = own(o, key);
  if (typeof value !== "boolean") throw new SliceError(child(path, key), "true or false");
  return value;
}

function readStatementRow(value: unknown, path: string, periods: number) {
  const r = rec(value, path);
  const cellsPath = child(path, "cells");
  const cells = list(r, "cells", path, (item, p) => shownOf(item, p));
  if (cells.length !== periods) {
    throw new SliceError(cellsPath, `${String(periods)} cells, one for each period`);
  }
  return { label: named(r, "label", path), cells, emphasis: bool(r, "emphasis", path) };
}

function readStatement(s: Rec, path: string, traces: Traces): RecordBlock {
  const periodsPath = child(path, "periods");
  const periods = some(
    list(s, "periods", path, (item, p) => {
      if (typeof item !== "string" || item === "") throw new SliceError(p, "a non-empty string");
      return item;
    }),
    periodsPath,
  );
  periods.forEach((period, index) => {
    if (periods.indexOf(period) !== index) {
      throw new SliceError(nth(periodsPath, index), "a period not used by an earlier one");
    }
  });
  const rowsPath = child(path, "rows");
  return {
    kind: "statement",
    nav: navLabel(s, "nav", path),
    title: named(s, "title", path),
    stub: named(s, "stub", path),
    basis: gradeOrNull(s, "basis", path),
    periods,
    rows: some(
      unique(
        list(s, "rows", path, (item, p) => readStatementRow(item, p, periods.length)),
        rowsPath,
        (row) => row.label,
        "label",
      ),
      rowsPath,
    ),
    trace: traceKey(s, "trace", path, traces),
  };
}

const CHARTS = ["stack", "columns", "bullet", "bridge", "scatter", "range"] as const;

function readChartColumns(c: Rec, path: string) {
  const columnsPath = child(path, "columns");
  const columns = some(
    unique(
      list(c, "columns", path, (item, p) => {
        const column = rec(item, p);
        return {
          label: named(column, "label", p),
          align: oneOf(column, "align", p, ["left", "right"]),
        };
      }),
      columnsPath,
      (column) => column.label,
      "label",
    ),
    columnsPath,
  );
  if (columns[0]?.align !== "left") {
    throw new SliceError(
      child(nth(columnsPath, 0), "align"),
      "left: the kit draws the label column left",
    );
  }
  columns.forEach((column, index) => {
    if (index >= CHART_TABLE_LIMITS.columns && column.align === "left") {
      throw new SliceError(
        child(nth(columnsPath, index), "align"),
        `right: only the first ${String(CHART_TABLE_LIMITS.columns)} columns can be left`,
      );
    }
  });
  return columns;
}

/** A table cell: text, or a figure; the label cell of a row is text. */
function readChartCell(value: unknown, path: string): Cell | string {
  if (typeof value !== "string") return shownOf(value, path);
  if (value === "") throw new SliceError(path, "a non-empty string");
  return value;
}

function readChartRow(value: unknown, path: string, width: number) {
  const r = rec(value, path);
  const cellsPath = child(path, "cells");
  const cells = list(r, "cells", path, readChartCell);
  if (cells.length !== width) {
    throw new SliceError(cellsPath, `${String(width)} cells, one for each column`);
  }
  if (typeof cells[0] !== "string") throw new SliceError(nth(cellsPath, 0), "the row's label");
  return { cells, emphasis: bool(r, "emphasis", path) };
}

/** Footnotes are sentences, each used once: the page keys them by their text. */
function readFootnotes(c: Rec, path: string): string[] {
  const notes = list(c, "footnotes", path, (item, p) => {
    if (typeof item !== "string" || item === "") throw new SliceError(p, "a non-empty string");
    return item;
  });
  notes.forEach((note, index) => {
    if (notes.indexOf(note) !== index) {
      throw new SliceError(
        nth(child(path, "footnotes"), index),
        "a footnote not used by an earlier one",
      );
    }
  });
  return notes;
}

function readChartTable(c: Rec, path: string, traces: Traces): RecordBlock {
  const columns = readChartColumns(c, path);
  const rowsPath = child(path, "rows");
  const rows = some(
    list(c, "rows", path, (item, p) => readChartRow(item, p, columns.length)),
    rowsPath,
  );
  rows.forEach((row, index) => {
    if (index >= CHART_TABLE_LIMITS.rows && row.emphasis) {
      throw new SliceError(
        child(nth(rowsPath, index), "emphasis"),
        `false: only the first ${String(CHART_TABLE_LIMITS.rows)} rows can be emphasised`,
      );
    }
  });
  return {
    kind: "chartTable",
    nav: navLabel(c, "nav", path),
    title: named(c, "title", path),
    chart: oneOf(c, "chart", path, CHARTS),
    note: gradeOrNull(c, "note", path),
    columns,
    rows,
    footnotes: readFootnotes(c, path),
    trace: traceKey(c, "trace", path, traces),
  };
}

function readRecord(value: unknown, path: string, traces: Traces): RecordBlock {
  const r = rec(value, path);
  switch (
    oneOf(r, "kind", path, [
      "matrix",
      "watch",
      "questions",
      "edges",
      "metrics",
      "measures",
      "facts",
      "status",
      "statement",
      "chartTable",
      "gap",
    ])
  ) {
    case "matrix":
      return readMatrix(r, path, traces);
    case "watch":
      return readWatch(r, path, traces);
    case "questions":
      return readQuestions(r, path, traces);
    case "edges":
      return readEdges(r, path);
    case "metrics":
      return readMetrics(r, path, traces);
    case "measures":
      return readMeasures(r, path, traces);
    case "facts":
      return readFacts(r, path, traces);
    case "status":
      return readStatus(r, path, traces);
    case "statement":
      return readStatement(r, path, traces);
    case "chartTable":
      return readChartTable(r, path, traces);
    case "gap":
      return {
        kind: "gap",
        nav: navLabel(r, "nav", path),
        title: named(r, "title", path),
        reason: named(r, "reason", path),
      };
  }
}

function readBody(value: unknown, path: string, traces: Traces): DeliveredBody | BlockedBody {
  const b = rec(value, path);
  if (oneOf(b, "kind", path, ["delivered", "blocked"]) === "blocked") {
    const linkPath = child(path, "gapsLink");
    return {
      kind: "blocked",
      reason: str(b, "reason", path),
      note: str(b, "note", path),
      gapsLink: { label: str(rec(own(b, "gapsLink"), linkPath), "label", linkPath) },
    };
  }
  return {
    kind: "delivered",
    bottomLine: readBottomLine(own(b, "bottomLine"), child(path, "bottomLine"), traces),
    findings: some(
      unique(
        list(b, "findings", path, (f, p) => readFinding(f, p, traces)),
        child(path, "findings"),
        (f) => f.number,
        "number",
      ),
      child(path, "findings"),
    ),
    contrary: optionalView(b, "contrary", path, traces),
    changeView: optionalView(b, "changeView", path, traces),
    records: unique(
      list(b, "records", path, (item, p) => readRecord(item, p, traces)),
      child(path, "records"),
      (block) => block.title,
      "title",
    ),
    limitations: readLimitations(own(b, "limitations"), child(path, "limitations"), traces),
  };
}

function readModule(value: unknown, path: string, traces: Traces): Module {
  const m = rec(value, path);
  const body = readBody(own(m, "body"), child(path, "body"), traces);
  return {
    id: str(m, "id", path),
    name: str(m, "name", path),
    state: oneOf(m, "state", path, body.kind === "blocked" ? BLOCKED_STATES : DELIVERED_STATES),
    body,
  };
}

/** A run's modules: each id and name used once. A run may hold none. */
function readRunModules(r: Rec, path: string, traces: Traces): Module[] {
  const modulesPath = child(path, "modules");
  const modules = unique(
    list(r, "modules", path, (m, p) => readModule(m, p, traces)),
    modulesPath,
    (m) => m.id,
    "id",
  );
  return unique(modules, modulesPath, (m) => m.name, "name");
}

/** Every item that opens a module names one this run holds. */
function opensHeld(
  items: readonly { module: string | null }[],
  held: ReadonlySet<string>,
  path: string,
): void {
  for (const [index, item] of items.entries()) {
    if (item.module !== null && !held.has(item.module)) {
      throw new SliceError(child(nth(path, index), "module"), "a module this run holds");
    }
  }
}

/** An item that opens a module carries the state that module holds, word for word. */
function statesMatch(
  items: readonly { module: string | null; state: string }[],
  modules: readonly Module[],
  path: string,
): void {
  for (const [index, item] of items.entries()) {
    const held = modules.find((m) => m.id === item.module);
    if (held !== undefined && held.state !== item.state) {
      throw new SliceError(
        child(nth(path, index), "state"),
        `the state ${held.state} its module holds`,
      );
    }
  }
}

/**
 * The module names a collapsed item's lead lists, in order, each followed by ", " or the closing
 * full stop. Names hold commas themselves, so each is matched whole against the run's own names.
 * `null` when the lead is not such a list.
 */
function namesListed(lead: string, names: readonly string[]): string[] | null {
  const listed: string[] = [];
  let rest = lead.endsWith(".") ? lead.slice(0, -1) : null;
  while (rest !== null && rest !== "") {
    const left: string = rest;
    const name = names.find((n) => left === n || left.startsWith(`${n}, `));
    if (name === undefined) return null;
    listed.push(name);
    rest = left === name ? "" : left.slice(name.length + 2);
  }
  return rest === null ? null : listed;
}

/** A collapsed item's title opens with the count of the modules it stands for. */
const COLLAPSED_TITLE = /^(\d+) modules? /;

/**
 * A collapsed item (one that opens no module and whose title counts modules) lists, in its lead,
 * only modules the run holds, and as many as its title says.
 */
function namesHeld(
  items: readonly { title: string; lead: string; module: string | null }[],
  modules: readonly Module[],
  path: string,
): void {
  const names = modules.map((m) => m.name);
  for (const [index, item] of items.entries()) {
    const counted = item.module === null ? COLLAPSED_TITLE.exec(item.title) : null;
    if (counted === null) continue;
    const listed = namesListed(item.lead, names);
    if (listed === null) {
      throw new SliceError(child(nth(path, index), "lead"), "the names of modules this run holds");
    }
    if (listed.length !== Number(counted[1])) {
      throw new SliceError(
        child(nth(path, index), "title"),
        "the count of the modules its lead names",
      );
    }
  }
}

/** The first module is the first one the run holds, and absent exactly when it holds none. */
function firstHeld(first: string | null, modules: readonly Module[] | null, path: string): void {
  const wanted = modules?.[0]?.id ?? null;
  if (first !== wanted) {
    throw new SliceError(
      child(child(path, "head"), "firstModule"),
      wanted === null ? "null for a run with no modules" : "the first module this run holds",
    );
  }
}

const FILE_STATES = ["Read in full", "Read in part", "Unreadable"] as const satisfies FileState[];

/** The modules the filter lists, by id: what a reader names must be one of them. */
type Held = ReadonlyMap<string, Reader>;

function heldModule(held: Held, id: string, path: string): Reader {
  const found = held.get(id);
  if (found === undefined) throw new SliceError(path, "a module the module filter lists");
  return found;
}

function readReader(value: unknown, path: string, held: Held): Reader {
  if (typeof value !== "string") throw new SliceError(path, "a module id");
  return heldModule(held, value, path);
}

/** The "+N" avatar: its text counts its ids, so a reader of the page never sees a count that disagrees. */
function readMore(r: Rec, path: string, held: Held): SourceFile["readers"]["more"] {
  if (own(r, "more") === null) return null;
  const m = rec(own(r, "more"), path);
  const ids = some(
    list(m, "ids", path, (item, p) => {
      if (typeof item !== "string") throw new SliceError(p, "a string");
      return heldModule(held, item, p).id;
    }),
    child(path, "ids"),
  );
  if (str(m, "text", path) !== `+${String(ids.length)}`) {
    throw new SliceError(child(path, "text"), `+${String(ids.length)}, one for each id`);
  }
  return { text: named(m, "text", path), label: named(m, "label", path), ids };
}

function readReaders(f: Rec, path: string, held: Held): SourceFile["readers"] {
  const readersPath = child(path, "readers");
  const r = rec(own(f, "readers"), readersPath);
  const shownPath = child(readersPath, "shown");
  const shown = list(r, "shown", readersPath, (item, p) => readReader(item, p, held));
  const more = readMore(r, child(readersPath, "more"), held);
  const everyone = [...shown.map((reader) => reader.id), ...(more?.ids ?? [])];
  everyone.forEach((id, index) => {
    if (everyone.indexOf(id) === index) return;
    const inMore = index - shown.length;
    const at =
      inMore < 0 ? nth(shownPath, index) : nth(child(child(readersPath, "more"), "ids"), inMore);
    throw new SliceError(at, "a module that reads this file once");
  });
  return { shown, more };
}

function readFile(value: unknown, path: string, held: Held): SourceFile {
  const f = rec(value, path);
  const state = oneOf(f, "state", path, FILE_STATES);
  const why = gradeOrNull(f, "why", path);
  if (state === "Unreadable" && why === null) {
    throw new SliceError(child(path, "why"), "the reason an unreadable file gives");
  }
  return {
    name: named(f, "name", path),
    kind: named(f, "kind", path),
    size: named(f, "size", path),
    state,
    why,
    readersLabel: named(f, "readersLabel", path),
    readers: readReaders(f, path, held),
    hash: named(f, "hash", path),
  };
}

function readDownload(value: unknown, path: string): Download {
  const d = rec(value, path);
  const href = gradeOrNull(d, "href", path);
  const reason = gradeOrNull(d, "reason", path);
  if (href === null && reason === null) {
    throw new SliceError(child(path, "reason"), "the reason no download is offered");
  }
  if (href !== null && reason !== null) {
    throw new SliceError(child(path, "reason"), "null beside a download that is offered");
  }
  return { label: named(d, "label", path), href, reason };
}

function readSummary(value: unknown, path: string, traces: Traces): Evidence["summary"] {
  const s = rec(value, path);
  const deliveredPath = child(path, "delivered");
  const delivered = rec(own(s, "delivered"), deliveredPath);
  const runPath = child(path, "run");
  const run = rec(own(s, "run"), runPath);
  const takePath = child(path, "take");
  const take = rec(own(s, "take"), takePath);
  const countsPath = child(path, "counts");
  return {
    delivered: {
      note: gradeOrNull(delivered, "note", deliveredPath),
      progress: readProgress(own(delivered, "progress"), child(deliveredPath, "progress")),
    },
    counts: some(
      unique(
        list(s, "counts", path, (item, p) => readMetric(item, p, traces)),
        countsPath,
        (count) => count.label,
        "label",
      ),
      countsPath,
    ),
    run: { code: named(run, "code", runPath), hash: named(run, "hash", runPath) },
    take: {
      text: named(take, "text", takePath),
      download: readDownload(own(take, "download"), child(takePath, "download")),
    },
  };
}

/** Whether `text` names `n` as a whole number, so a delivered label can be held to the rows it counts. */
const namesNumber = (text: string, n: number): boolean =>
  new RegExp(`(?<!\\d)${String(n)}(?!\\d)`).test(text);

function readSources(value: unknown, path: string, held: Held): Evidence["sources"] {
  const s = rec(value, path);
  const filesPath = child(path, "files");
  const files = some(
    list(s, "files", path, (item, p) => readFile(item, p, held)),
    filesPath,
  );
  for (const field of ["name", "hash"] as const) {
    unique(files, filesPath, (file) => file[field], field);
  }
  const visible = num(s, "visible", path);
  if (!Number.isInteger(visible) || visible < 1 || visible > files.length) {
    throw new SliceError(child(path, "visible"), "a whole number from 1 to the number of files");
  }
  const moreLabel = gradeOrNull(s, "moreLabel", path);
  if (visible < files.length !== (moreLabel !== null)) {
    throw new SliceError(child(path, "moreLabel"), "text exactly when a file is held back");
  }
  const hidden = files.length - visible;
  if (moreLabel !== null && !namesNumber(moreLabel, hidden)) {
    throw new SliceError(
      child(path, "moreLabel"),
      `a label that names the ${String(hidden)} held back`,
    );
  }
  return { files, visible, moreLabel };
}

/** The filter's options: each is a module the run holds, with its own name, and delivered initials. */
function readFilter(e: Rec, path: string, modules: readonly Module[]): Reader[] {
  const filterPath = child(path, "moduleFilter");
  return unique(
    list(e, "moduleFilter", path, (item, p) => {
      const o = rec(item, p);
      const id = str(o, "id", p);
      const name = str(o, "name", p);
      const module = modules.find((m) => m.id === id);
      if (module === undefined) throw new SliceError(child(p, "id"), "a module this run holds");
      if (module.name !== name) throw new SliceError(child(p, "name"), "the name of that module");
      return { id, name, initials: named(o, "initials", p) };
    }),
    filterPath,
    (option) => option.id,
    "id",
  );
}

/** The modules a run holds by id, for a row that names the module it sits in. */
type Seats = ReadonlyMap<string, string>;

/** The module a row sits in: an id the run holds and that module's own name, or the Overview, with no id. */
function readSeat(o: Rec, path: string, seats: Seats) {
  const id = strOrNull(o, "moduleId", path);
  const module = named(o, "module", path);
  if (id === null) {
    if (module !== "Overview") {
      throw new SliceError(child(path, "module"), "Overview, for an item with no module");
    }
    return { module, moduleId: null };
  }
  const held = seats.get(id);
  if (held === undefined) throw new SliceError(child(path, "moduleId"), "a module this run holds");
  if (held !== module) throw new SliceError(child(path, "module"), "the name of that module");
  return { module, moduleId: id };
}

function readTraceRow(value: unknown, path: string, seats: Seats): TraceRow {
  const r = rec(value, path);
  return {
    id: named(r, "id", path),
    item: named(r, "item", path),
    ...readSeat(r, path, seats),
    kind: named(r, "kind", path),
    value: cell(r, "value", path),
    sources: named(r, "sources", path),
    calc: own(r, "calc") === null ? null : readTree(own(r, "calc"), child(path, "calc")),
    note: gradeOrNull(r, "note", path),
  };
}

const TRACE_HEADS = ["id", "item", "value", "module", "kind", "sources"] as const;

function readTraceTable(value: unknown, path: string, seats: Seats): TraceTable {
  const t = rec(value, path);
  const columnsPath = child(path, "columns");
  const heads = rec(own(t, "columns"), columnsPath);
  const rowsPath = child(path, "rows");
  return {
    title: named(t, "title", path),
    description: named(t, "description", path),
    columns: Object.fromEntries(
      TRACE_HEADS.map((key) => [key, named(heads, key, columnsPath)]),
    ) as TraceTable["columns"],
    rows: unique(
      list(t, "rows", path, (item, p) => readTraceRow(item, p, seats)),
      rowsPath,
      (row) => row.id,
      "id",
    ),
  };
}

/** A tab's delivered count is the number of rows its page holds; the reader refuses one that disagrees. */
function countsRows(tabs: Rec, key: string, path: string, rows: number): string {
  const text = named(tabs, key, path);
  if (text !== String(rows)) {
    throw new SliceError(child(path, key), `${String(rows)}, the number of rows it holds`);
  }
  return text;
}

/** Every item a trace opens is a row of the Trace tab. */
function itemsHeld(traces: Traces, path: string, trace: TraceTable): void {
  const held = new Set(trace.rows.map((row) => row.id));
  for (const [key, one] of Object.entries(traces)) {
    if (!held.has(one.evidenceItem)) {
      throw new SliceError(child(child(path, key), "evidenceItem"), "a row id of evidence.trace");
    }
  }
}

const GAP_SEVERITIES = Object.keys(STATUS_SETS["Gap severity"]) as GapSeverity[];
const GAP_FORMS = ["gap", "withheld", "blocked", "missing"] as const satisfies GapForm[];
const GAP_PAGES = ["overview", "module"] as const;

function readGapRow(value: unknown, path: string, seats: Seats): GapRow {
  const r = rec(value, path);
  const moduleId = str(r, "moduleId", path);
  const { module } = readSeat(r, path, seats);
  const wherePath = child(path, "where");
  const where = rec(own(r, "where"), wherePath);
  return {
    id: named(r, "id", path),
    gap: named(r, "gap", path),
    module,
    moduleId,
    reason: named(r, "reason", path),
    shownAs: oneOf(r, "shownAs", path, GAP_FORMS),
    where: {
      page: oneOf(where, "page", wherePath, GAP_PAGES),
      label: named(where, "label", wherePath),
    },
  };
}

function readGapGroup(value: unknown, path: string, seats: Seats): GapTable["groups"][number] {
  const g = rec(value, path);
  const rows = some(
    list(g, "rows", path, (item, p) => readGapRow(item, p, seats)),
    child(path, "rows"),
  );
  const count = named(g, "count", path);
  if (count !== String(rows.length)) {
    throw new SliceError(
      child(path, "count"),
      `${String(rows.length)}, the number of rows it holds`,
    );
  }
  return { severity: oneOf(g, "severity", path, GAP_SEVERITIES), count, rows };
}

/** A run with no gap has no group. Groups run High, Medium, Low as delivered, none twice; a gap's id is the run's own, in one group only. */
function readGapTable(value: unknown, path: string, seats: Seats): GapTable {
  const t = rec(value, path);
  const columnsPath = child(path, "columns");
  const heads = rec(own(t, "columns"), columnsPath);
  const groupsPath = child(path, "groups");
  const groups = list(t, "groups", path, (item, p) => readGapGroup(item, p, seats));
  const seen = new Set<string>();
  groups.forEach((group, g) => {
    const before = groups[g - 1];
    if (
      before !== undefined &&
      GAP_SEVERITIES.indexOf(group.severity) <= GAP_SEVERITIES.indexOf(before.severity)
    ) {
      throw new SliceError(
        child(nth(groupsPath, g), "severity"),
        "a severity after the one before it",
      );
    }
    group.rows.forEach((row, r) => {
      if (seen.has(row.id)) {
        throw new SliceError(
          child(nth(child(nth(groupsPath, g), "rows"), r), "id"),
          "an id not used by an earlier gap",
        );
      }
      seen.add(row.id);
    });
  });
  return {
    title: named(t, "title", path),
    description: named(t, "description", path),
    columns: Object.fromEntries(
      ["id", "gap", "module", "reason", "shownAs"].map((key) => [
        key,
        named(heads, key, columnsPath),
      ]),
    ) as GapTable["columns"],
    groups,
  };
}

function readEvidence(value: unknown, path: string, traces: Traces, modules: Module[]): Evidence {
  const e = rec(value, path);
  const moduleFilter = readFilter(e, path, modules);
  const held: Held = new Map(moduleFilter.map((option) => [option.id, option]));
  const tabsPath = child(path, "tabs");
  const tabs = rec(own(e, "tabs"), tabsPath);
  const seats: Seats = new Map(modules.map((m) => [m.id, m.name]));
  const trace = readTraceTable(own(e, "trace"), child(path, "trace"), seats);
  const gaps = readGapTable(own(e, "gaps"), child(path, "gaps"), seats);
  return {
    intro: named(e, "intro", path),
    moduleFilter,
    tabs: {
      trace: countsRows(tabs, "trace", tabsPath, trace.rows.length),
      sources: named(tabs, "sources", tabsPath),
      gaps: countsRows(
        tabs,
        "gaps",
        tabsPath,
        gaps.groups.reduce((n, g) => n + g.rows.length, 0),
      ),
    },
    summary: readSummary(own(e, "summary"), child(path, "summary"), traces),
    sources: readSources(own(e, "sources"), child(path, "sources"), held),
    trace,
    gaps,
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
  const modulesPath = child(path, "modules");
  const evidencePath = child(path, "evidence");
  if (loading) {
    firstHeld(base.head.firstModule, null, path);
    if (own(r, "overview") !== null) throw new SliceError(overviewPath, "null for a loading run");
    if (own(r, "changes") !== null) throw new SliceError(changesPath, "null for a loading run");
    if (own(r, "modules") !== null) throw new SliceError(modulesPath, "null for a loading run");
    if (own(r, "evidence") !== null) throw new SliceError(evidencePath, "null for a loading run");
    return { ...base, loading, overview: null, changes: null, modules: null, evidence: null };
  }
  const overview = readOverview(own(r, "overview"), overviewPath, base.traces);
  const changes = readChanges(own(r, "changes"), changesPath, base.traces);
  const modules = readRunModules(r, path, base.traces);
  firstHeld(base.head.firstModule, modules, path);
  const held = new Set(modules.map((m) => m.id));
  const overviewItems = child(child(overviewPath, "modules"), "items");
  opensHeld(overview.modules.items, held, overviewItems);
  statesMatch(overview.modules.items, modules, overviewItems);
  namesHeld(overview.modules.items, modules, overviewItems);
  if (changes.kind === "compared") {
    const changeItems = child(child(changesPath, "modules"), "items");
    opensHeld(changes.modules.items, held, changeItems);
    namesHeld(changes.modules.items, modules, changeItems);
  }
  const evidence = readEvidence(own(r, "evidence"), evidencePath, base.traces, modules);
  itemsHeld(base.traces, tracesPath, evidence.trace);
  const gapsPath = child(child(overviewPath, "limitations"), "gapsLink");
  const gapCount = evidence.gaps.groups.reduce((n, g) => n + g.rows.length, 0);
  if (!namesNumber(overview.limitations.gapsLink.label, gapCount)) {
    throw new SliceError(
      child(gapsPath, "label"),
      `a label that names the ${String(gapCount)} gaps`,
    );
  }
  return { ...base, loading, overview, changes, modules, evidence };
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
