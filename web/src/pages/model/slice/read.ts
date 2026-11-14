import { STATUS_SETS } from "@/components/status/sets";
import type { SliceResult } from "../../route-table";
import {
  addressOrNull,
  SliceError,
  address,
  arrayOf,
  bool,
  child,
  distinct,
  distinctTraceNames,
  atLeastOne,
  at,
  fail,
  is,
  object,
  oneOf,
  orNull,
  text,
  textOrNull,
  tagged,
  yes,
  type Reader,
} from "./reader-kit";
import { analysis, checkAnalysis } from "./read-analysis";
import { checkSections, sections } from "./read-sections";
import type {
  Fact,
  Cell,
  CaseCard,
  FrontPage,
  GapItem,
  LimitationsPage,
  Limitation,
  Metric,
  MetricValue,
  ModelRun,
  ModelSlice,
  RowKind,
  RunHeader,
  RunLinks,
  Part,
  PartPage,
  RunState,
  Statement,
  StatementColumn,
  StatementRow,
  StatementsPage,
} from "./types";

const runState = oneOf(Object.keys(STATUS_SETS["Run states"]) as RunState[]);

const header = object<RunHeader>({
  issuerName: text,
  asOf: text,
  purpose: text,
  state: runState,
  sample: bool,
});
const links = object<RunLinks>({
  library: address,
  report: address,
  evidence: address,
  evidenceGaps: address,
});
const limitation = object<Limitation>({
  title: text,
  label: text,
  text: text,
  trace: addressOrNull,
});
const gap = object<GapItem>({ title: text, reason: text });
const limitations = object<LimitationsPage>({
  count: text,
  gapsLinkText: text,
  lead: text,
  items: arrayOf(limitation),
  notEstablished: object({ count: text, items: arrayOf(gap) }),
});
const metricValue: Reader<MetricValue> = (value, path) =>
  typeof value === "object" && value !== null && Object.hasOwn(value, "withheld")
    ? object<{ withheld: true }>({ withheld: yes })(value, path)
    : object<{ text: string | null }>({ text: textOrNull })(value, path);
const metricFields = object<Metric>({
  label: text,
  definition: text,
  value: metricValue,
  delta: textOrNull,
  note: textOrNull,
  trace: addressOrNull,
});
/** A delta beside a missing or withheld value would be dropped by the page, so it is refused. */
const metric: Reader<Metric> = (value, path) => {
  const read = metricFields(value, path);
  const noFigure = "withheld" in read.value || read.value.text === null;
  if (noFigure && read.delta !== null) {
    return fail(child(path, "delta"), "expected null beside a missing or withheld value");
  }
  return read;
};
const fact = object<Fact>({ label: text, value: text, trace: addressOrNull });
const part = object<Part>({
  title: text,
  text: text,
  to: orNull<PartPage>(["analysis", "statements", "portfolio-fit"]),
  trace: addressOrNull,
});
const front = object<FrontPage>({
  bottomLine: object({ lead: text, rest: text, trace: addressOrNull }),
  headline: object({ period: text, metrics: arrayOf(metric) }),
  covers: object({ facts: arrayOf(fact) }),
  parts: arrayOf(part),
});
const caseCard = object<CaseCard>({
  name: text,
  tag: text,
  assumption: text,
  leavesOut: text,
  note: textOrNull,
  trace: addressOrNull,
});

const position: Reader<number> = (value, path) =>
  typeof value === "number" && Math.abs(value) <= 1
    ? value
    : fail(path, "expected a number from -1 to 1");
const cell = tagged<Cell>({
  figure: object({ kind: is("figure"), text: text, pos: position }),
  missing: object({ kind: is("missing"), reason: textOrNull }),
  withheld: object({ kind: is("withheld"), reason: textOrNull }),
});
const cellEntry: Reader<Cell | Cell[]> = (value, path) =>
  Array.isArray(value) ? arrayOf(cell)(value, path) : cell(value, path);
const column = tagged<StatementColumn>({
  actual: object({ kind: is("actual"), period: text, note: text }),
  forecast: object({
    kind: is("forecast"),
    period: text,
    notes: arrayOf(object({ text: text })),
  }),
  empty: object({ kind: is("empty"), period: text, note: textOrNull, reason: text }),
});
const rowKind = oneOf<RowKind>(["plain", "subtotal", "total"]);
const statementRow = object<StatementRow>({
  label: text,
  kind: rowKind,
  gap: bool,
  trace: addressOrNull,
  cells: arrayOf(cellEntry),
});
const statements = object<StatementsPage>({
  intro: text,
  columns: arrayOf(column),
  statements: arrayOf(object<Statement>({ name: text, rows: arrayOf(statementRow) })),
  ...sections,
});

/** Every list the front page draws holds something, and no two of its trace controls share a name. */
function checkFront(page: FrontPage, path: string): void {
  atLeastOne(page.headline.metrics, child(path, "headline.metrics"), "metric");
  atLeastOne(page.covers.facts, child(path, "covers.facts"), "fact");
  atLeastOne(page.parts, child(path, "parts"), "part");
  distinctTraceNames([
    { name: "the bottom line", trace: page.bottomLine.trace, where: child(path, "bottomLine") },
    ...page.headline.metrics.map((m, i) => ({
      name: m.label,
      trace: m.trace,
      where: `${at(child(path, "headline.metrics"), i)}.label`,
    })),
    ...page.covers.facts.map((f, i) => ({
      name: f.label,
      trace: f.trace,
      where: `${at(child(path, "covers.facts"), i)}.label`,
    })),
    ...page.parts.map((p, i) => ({
      name: p.title,
      trace: p.trace,
      where: `${at(child(path, "parts"), i)}.title`,
    })),
  ]);
}

/** The limitations list holds something, and no two of its trace controls share a name. */
function checkLimitations(page: LimitationsPage, path: string): void {
  atLeastOne(page.items, child(path, "items"), "limitation");
  distinctTraceNames(
    page.items.map((l, i) => ({
      name: l.title,
      trace: l.trace,
      where: `${at(child(path, "items"), i)}.title`,
    })),
  );
}

/**
 * The statements page's trace controls: the cases, the five charts and, for each statement (one
 * is open at a time), its rows. No two controls that can be drawn together share a name.
 */
function checkStatementNames(
  page: StatementsPage,
  cases: readonly CaseCard[],
  casesPath: string,
  path: string,
): void {
  const shared = [
    ...cases.map((c, i) => ({ name: c.name, trace: c.trace, where: `${at(casesPath, i)}.name` })),
    ...page.bridges.map((b, i) => ({
      name: b.title,
      trace: b.trace,
      where: `${at(child(path, "bridges"), i)}.title`,
    })),
    {
      name: page.comparison.title,
      trace: page.comparison.trace,
      where: child(path, "comparison.title"),
    },
    {
      name: page.debt.stack.title,
      trace: page.debt.stack.trace,
      where: child(path, "debt.stack.title"),
    },
    {
      name: page.debt.maturities.title,
      trace: page.debt.maturities.trace,
      where: child(path, "debt.maturities.title"),
    },
    { name: page.recovery.title, trace: page.recovery.trace, where: child(path, "recovery.title") },
  ];
  page.statements.forEach((statement, s) => {
    distinctTraceNames([
      ...shared,
      ...statement.rows.map((row, r) => ({
        name: row.label,
        trace: row.trace,
        where: `${at(`${child(path, "statements")}[${String(s)}].rows`, r)}.label`,
      })),
    ]);
  });
}

/** The statements must hold one note and one cell per case in every forecast column. */
function checkStatements(page: StatementsPage, cases: number, path: string): void {
  atLeastOne(page.columns, `${path}.columns`, "column");
  if (page.statements.length === 0) {
    fail(`${path}.statements`, "expected at least one statement");
  }
  page.statements.forEach((statement, i) => {
    if (page.statements.findIndex((other) => other.name === statement.name) !== i) {
      fail(`${path}.statements[${String(i)}].name`, "expected a name no other statement has");
    }
  });
  const plural = (n: number, noun: string) => `${String(n)} ${noun}${n === 1 ? "" : "s"}`;
  page.columns.forEach((col, i) => {
    if (col.kind === "forecast" && col.notes.length !== cases) {
      fail(
        `${path}.columns[${String(i)}].notes`,
        `expected ${plural(cases, "note")}, one per case`,
      );
    }
  });
  const shown = page.columns.filter((col) => col.kind !== "empty");
  page.statements.forEach((statement, s) => {
    atLeastOne(statement.rows, `${path}.statements[${String(s)}].rows`, "row");
    statement.rows.forEach((row, r) => {
      const rowPath = `${path}.statements[${String(s)}].rows[${String(r)}].cells`;
      if (row.cells.length !== shown.length) {
        fail(rowPath, `expected ${String(shown.length)} entries, one per column that is not empty`);
      }
      row.cells.forEach((entry, c) => {
        const cellPath = `${rowPath}[${String(c)}]`;
        if (shown[c]?.kind === "forecast") {
          if (!Array.isArray(entry) || entry.length !== cases) {
            fail(cellPath, `expected a list of ${String(cases)} cells, one per case`);
          }
        } else if (Array.isArray(entry)) {
          fail(cellPath, "expected one cell for an actual column");
        }
      });
    });
  });
}

const runFields = object<ModelRun>({
  issuer: text,
  run: text,
  header,
  links,
  cases: arrayOf(caseCard),
  front,
  analysis,
  statements,
  limitations,
});
const run: Reader<ModelRun> = (value, path) => {
  const read = runFields(value, path);
  if (read.cases.length === 0) fail(child(path, "cases"), "expected at least one case");
  if (read.cases.length !== 2) {
    fail(child(path, "cases"), "expected two cases, the side by side chart draws two");
  }
  const [first, second] = read.cases;
  if (first?.name === second?.name) {
    fail(`${child(path, "cases")}[1].name`, "expected a name the other case does not have");
  }
  checkFront(read.front, child(path, "front"));
  checkLimitations(read.limitations, child(path, "limitations"));
  checkAnalysis(read.analysis, child(path, "analysis"));
  checkStatements(read.statements, read.cases.length, child(path, "statements"));
  checkSections(read.statements, read.cases, child(path, "statements"));
  checkStatementNames(read.statements, read.cases, child(path, "cases"), child(path, "statements"));
  return read;
};
const sliceFields = object<ModelSlice>({ runs: arrayOf(run) });
/** A page finds its run by issuer and run, so two runs with the same pair would hide the second. */
const slice: Reader<ModelSlice> = (value, path) => {
  const read = sliceFields(value, path);
  distinct(read.runs, (r) => `${r.issuer}\u0000${r.run}`, child(path, "runs"), "run", "run");
  return read;
};

/** `undefined` is absent; any other source is read in full or named invalid at its first bad path. */
export function readSlice(source: unknown): SliceResult<ModelSlice> {
  if (source === undefined) return { kind: "absent" };
  try {
    return { kind: "ok", data: slice(source, "") };
  } catch (error) {
    if (error instanceof SliceError) return { kind: "invalid", reason: error.message };
    throw error;
  }
}
