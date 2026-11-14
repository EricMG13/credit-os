import {
  addressOrNull,
  arrayOf,
  at,
  chartInfo,
  child,
  fail,
  is,
  num,
  numOrNull,
  object,
  oneOf,
  pairOf,
  tagged,
  text,
  textOrNull,
  type Reader,
} from "./reader-kit";
import type {
  Bridge,
  BridgeStep,
  CaseCard,
  ColumnsData,
  Comparison,
  ComparisonPanel,
  Published,
  Stack,
  StackPart,
  StatementsPage,
  Tick,
} from "./types";

const tick = object<Tick>({ value: num, label: text });

const present = <K extends "total" | "up" | "down">(kind: K) =>
  object({ label: text, kind: is(kind), from: num, to: num, text });
const step = tagged<BridgeStep>({
  total: present("total"),
  up: present("up"),
  down: present("down"),
  missing: object({ label: text, kind: is("missing") }),
});
export const bridge = object<Bridge>({
  ...chartInfo,
  yTicks: arrayOf(tick),
  caseSteps: arrayOf(arrayOf(step)),
  head: arrayOf(text),
  rows: arrayOf(object({ label: text, cells: arrayOf(textOrNull), trace: addressOrNull })),
});
const panel = object<ComparisonPanel>({
  measure: text,
  tableLabel: text,
  max: num,
  values: pairOf(numOrNull),
  texts: pairOf(textOrNull),
  trace: addressOrNull,
});
const comparison = object<Comparison>({
  ...chartInfo,
  rowLabels: pairOf(text),
  tableHead: text,
  panels: arrayOf(panel),
});
const part = object<StackPart>({ name: text, value: num, text, share: text, trace: addressOrNull });
const stack = object<Stack>({ ...chartInfo, head: arrayOf(text), parts: arrayOf(part) });
const columns = object<ColumnsData>({
  ...chartInfo,
  yTicks: arrayOf(tick),
  head: text,
  groups: arrayOf(object({ label: text, trace: addressOrNull })),
  series: arrayOf(object({ name: text, values: arrayOf(numOrNull), labels: arrayOf(textOrNull) })),
});
const publishedRecord = object<Published>({
  kind: oneOf(["markdown", "html"] as const),
  href: text,
});
/** `null`, or a record with kind and href; anything with neither key is not a published model. */
const published: Reader<Published | null> = (value, path) => {
  if (value === null) return null;
  const isRecord = typeof value === "object" && !Array.isArray(value);
  if (!isRecord || !("kind" in value || "href" in value)) {
    return fail(path, "expected null or an object with kind and href");
  }
  return publishedRecord(value, path);
};

/** The members the second half of the Model page adds to the statements page. */
export const sections = {
  bridges: arrayOf(bridge),
  comparison,
  debt: object<StatementsPage["debt"]>({ stack, maturities: columns }),
  recovery: columns,
  gap: object({ title: text, reason: text }),
  checkFigure: object({ title: text, text, href: text }),
  published,
};

/** Refuses the first item whose key an earlier item already has, at `path(i)`. */
function noRepeat<T>(
  list: readonly T[],
  key: (item: T) => string,
  path: (i: number) => string,
  message: string,
): void {
  list.forEach((item, i) => {
    if (list.findIndex((other) => key(other) === key(item)) !== i)
      fail(path(i), `expected ${message}`);
  });
}

function atLeastOne(list: readonly unknown[], path: string, noun: string): void {
  if (list.length === 0) fail(path, `expected at least one ${noun}`);
}

function exactly(list: readonly unknown[], n: number, path: string, what: string): void {
  if (list.length !== n) fail(path, `expected ${String(n)} ${what}`);
}

/** Caller ticks: two or more, rising from 0. Returns the last tick, the axis end. */
export function checkTicks(ticks: readonly Tick[], path: string): number {
  const last = ticks[ticks.length - 1];
  if (ticks.length < 2 || last === undefined) fail(path, "expected at least two ticks");
  ticks.forEach((t, i) => {
    const before = ticks[i - 1];
    if (i === 0 && t.value !== 0) fail(`${at(path, i)}.value`, "expected the first tick to be 0");
    if (before !== undefined && !(t.value > before.value)) {
      fail(`${at(path, i)}.value`, "expected ticks in rising order");
    }
  });
  return last.value;
}

/** A position that sits on the one zero baseline and inside the axis. */
function checkPosition(value: number, axisEnd: number, path: string): void {
  if (value < 0) fail(path, "expected a number of zero or more");
  if (value > axisEnd)
    fail(path, `expected a position within the axis (at most ${String(axisEnd)})`);
}

function checkStep(s: BridgeStep, axisEnd: number, path: string): void {
  if (s.kind === "missing") return;
  checkPosition(s.from, axisEnd, `${path}.from`);
  checkPosition(s.to, axisEnd, `${path}.to`);
  if (s.kind === "total" && s.from !== 0) fail(`${path}.from`, "expected 0 for a total");
  if (s.kind === "up" && s.to < s.from) {
    fail(`${path}.to`, "expected a position at or above from for an increase");
  }
  if (s.kind === "down" && s.to > s.from) {
    fail(`${path}.to`, "expected a position at or below from for a decrease");
  }
}

export function checkBridge(b: Bridge, cases: readonly CaseCard[], path: string): void {
  const axisEnd = checkTicks(b.yTicks, `${path}.yTicks`);
  exactly(b.caseSteps, cases.length, `${path}.caseSteps`, "lists of steps, one per case");
  b.caseSteps.forEach((steps, k) => {
    const where = at(`${path}.caseSteps`, k);
    atLeastOne(steps, where, "step");
    noRepeat(
      steps,
      (s) => s.label,
      (i) => `${at(where, i)}.label`,
      "a label no other step has",
    );
    steps.forEach((s, i) => {
      checkStep(s, axisEnd, at(where, i));
    });
  });
  const names = cases.map((c) => c.name);
  if (b.head.slice(1).join("\u0000") !== names.join("\u0000")) {
    fail(`${path}.head`, "expected the case names after the first heading, in order");
  }
  const steps = b.caseSteps[0] ?? [];
  exactly(b.rows, steps.length, `${path}.rows`, "rows, one per step");
  noRepeat(
    b.rows,
    (r) => r.label,
    (i) => `${at(`${path}.rows`, i)}.label`,
    "a label no other row has",
  );
  b.caseSteps.forEach((list, k) => {
    exactly(list, b.rows.length, at(`${path}.caseSteps`, k), "steps, one per row");
  });
  b.rows.forEach((row, r) => {
    const where = `${at(`${path}.rows`, r)}.cells`;
    exactly(row.cells, cases.length, where, "cells, one per case");
    row.cells.forEach((cell, k) => {
      const missing = b.caseSteps[k]?.[r]?.kind === "missing";
      if ((cell === null) !== missing) {
        fail(at(where, k), "expected null exactly where the step is missing");
      }
    });
  });
}

function checkComparison(c: Comparison, path: string): void {
  if (c.rowLabels[0] === c.rowLabels[1]) {
    fail(`${path}.rowLabels[1]`, "expected a label the other row does not have");
  }
  atLeastOne(c.panels, `${path}.panels`, "panel");
  noRepeat(
    c.panels,
    (p) => p.measure,
    (i) => `${at(`${path}.panels`, i)}.measure`,
    "a measure no other panel has",
  );
  noRepeat(
    c.panels,
    (p) => p.tableLabel,
    (i) => `${at(`${path}.panels`, i)}.tableLabel`,
    "a label no other panel has",
  );
  c.panels.forEach((p, i) => {
    const where = at(`${path}.panels`, i);
    if (!(p.max > 0)) fail(`${where}.max`, "expected a number above zero");
    p.values.forEach((v, k) => {
      const t = p.texts[k];
      if (v === null) {
        if (t !== null) fail(at(`${where}.texts`, k), "expected null beside a missing value");
        return;
      }
      if (v < 0) fail(at(`${where}.values`, k), "expected a number of zero or more");
      if (v > p.max) fail(at(`${where}.values`, k), "expected a number of at most the panel's max");
      if (t === null) fail(at(`${where}.texts`, k), "expected a text beside a present value");
    });
  });
}

function checkStack(s: Stack, path: string): void {
  atLeastOne(s.parts, `${path}.parts`, "part");
  noRepeat(
    s.parts,
    (p) => p.name,
    (i) => `${at(`${path}.parts`, i)}.name`,
    "a name no other part has",
  );
  s.parts.forEach((p, i) => {
    if (!(p.value > 0)) fail(`${at(`${path}.parts`, i)}.value`, "expected a number above zero");
  });
  exactly(s.head, 3, `${path}.head`, "entries, the label, amount and share headings");
}

function checkColumns(d: ColumnsData, path: string): void {
  const axisEnd = checkTicks(d.yTicks, `${path}.yTicks`);
  atLeastOne(d.groups, `${path}.groups`, "group");
  noRepeat(
    d.groups,
    (g) => g.label,
    (i) => `${at(`${path}.groups`, i)}.label`,
    "a label no other group has",
  );
  atLeastOne(d.series, `${path}.series`, "series");
  noRepeat(
    d.series,
    (s) => s.name,
    (i) => `${at(`${path}.series`, i)}.name`,
    "a name no other series has",
  );
  d.series.forEach((s, i) => {
    const where = at(`${path}.series`, i);
    exactly(s.values, d.groups.length, `${where}.values`, "entries, one per group");
    exactly(s.labels, d.groups.length, `${where}.labels`, "entries, one per group");
    s.values.forEach((v, g) => {
      const label = s.labels[g];
      if (v === null) {
        if (label !== null) fail(at(`${where}.labels`, g), "expected null beside a missing value");
        return;
      }
      checkPosition(v, axisEnd, at(`${where}.values`, g));
      if (label === null) fail(at(`${where}.labels`, g), "expected a label beside a present value");
    });
  });
}

/** Every rule a chart's own check enforces, so a slice that reads ok never throws in a chart. */
export function checkSections(
  page: StatementsPage,
  cases: readonly CaseCard[],
  path: string,
): void {
  atLeastOne(page.bridges, child(path, "bridges"), "bridge");
  noRepeat(
    page.bridges,
    (b) => b.title,
    (i) => `${at(child(path, "bridges"), i)}.title`,
    "a title no other bridge has",
  );
  page.bridges.forEach((b, i) => {
    checkBridge(b, cases, at(child(path, "bridges"), i));
  });
  checkComparison(page.comparison, child(path, "comparison"));
  checkStack(page.debt.stack, child(path, "debt.stack"));
  checkColumns(page.debt.maturities, child(path, "debt.maturities"));
  checkColumns(page.recovery, child(path, "recovery"));
}
