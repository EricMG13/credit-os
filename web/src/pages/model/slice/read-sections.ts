import {
  addressOrNull,
  arrayOf,
  at,
  chartInfo,
  child,
  fail,
  is,
  num,
  object,
  tagged,
  text,
  textOrNull,
} from "./reader-kit";
import type { Bridge, BridgeStep, CaseCard, StatementsPage, Tick } from "./types";

const tick = object<Tick>({ value: num, label: text });

const present = <K extends "total" | "up" | "down">(kind: K) =>
  object({ label: text, kind: is(kind), from: num, to: num, text });
const step = tagged<BridgeStep>({
  total: present("total"),
  up: present("up"),
  down: present("down"),
  missing: object({ label: text, kind: is("missing") }),
});
const bridge = object<Bridge>({
  ...chartInfo,
  yTicks: arrayOf(tick),
  caseSteps: arrayOf(arrayOf(step)),
  head: arrayOf(text),
  rows: arrayOf(object({ label: text, cells: arrayOf(textOrNull), trace: addressOrNull })),
});

/** The members the second half of the Model page adds to the statements page. */
export const sections = {
  bridges: arrayOf(bridge),
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
function checkTicks(ticks: readonly Tick[], path: string): number {
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

function checkBridge(b: Bridge, cases: readonly CaseCard[], path: string): void {
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
}
