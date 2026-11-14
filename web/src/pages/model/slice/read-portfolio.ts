import {
  addressOrNull,
  arrayOf,
  at,
  atLeastOne,
  bool,
  chartInfo as info,
  checkCells,
  checkPresence,
  child,
  distinct,
  fail,
  needCells,
  num,
  numOrNull,
  object,
  pairOf,
  text,
  textOrNull,
  type Reader,
} from "./reader-kit";
import type {
  HoldingsScatter,
  HoldingsStrips,
  Limits,
  LimitsColumn,
  PortfolioFitPage,
  RatingTile,
  Ratings,
  RelativeValue,
  ScatterAxis,
  ScatterRow,
  StripRow,
} from "./types";

const pairCells = pairOf(textOrNull);
const axis = object<ScatterAxis>({
  title: text,
  short: text,
  ticks: arrayOf(object({ value: num, label: text })),
});

const limitColumn = object<LimitsColumn>({
  label: text,
  exposure: numOrNull,
  limit: numOrNull,
  scaleMax: num,
  exposureText: textOrNull,
  limitText: textOrNull,
  cells: pairCells,
});
const limits = object<Limits>({ ...info, head: arrayOf(text), columns: arrayOf(limitColumn) });
const tile = object<RatingTile>({ label: text, value: textOrNull, caption: textOrNull });
const ratings = object<Ratings>({
  title: text,
  trace: addressOrNull,
  tiles: pairOf(tile),
});
const relativeValue = object<RelativeValue>({ title: text, part: text, reason: text });
const scatterRow = object<ScatterRow>({
  name: text,
  x: numOrNull,
  y: numOrNull,
  xText: textOrNull,
  yText: textOrNull,
  emphasis: bool,
  cells: pairCells,
});
const scatter = object<HoldingsScatter>({
  ...info,
  x: axis,
  y: axis,
  othersName: text,
  head: arrayOf(text),
  points: arrayOf(scatterRow),
});
const rangeRecord = object<{ low: number; high: number }>({ low: num, high: num });
/** `null`, or a record with low and high; anything with neither key is not a range. */
const range: Reader<{ low: number; high: number } | null> = (value, path) => {
  if (value === null) return null;
  const isRecord = typeof value === "object" && !Array.isArray(value);
  if (!isRecord || !("low" in value || "high" in value)) {
    return fail(path, "expected null or an object with low and high");
  }
  return rangeRecord(value, path);
};
const stripRow = object<StripRow>({
  label: text,
  rangeText: text,
  range,
  markers: arrayOf(object({ name: text, value: numOrNull, text: textOrNull })),
  axis: object({ min: num, max: num }),
  cells: arrayOf(textOrNull),
});
const strips = object<HoldingsStrips>({
  ...info,
  rangeLabel: text,
  head: arrayOf(text),
  rows: arrayOf(stripRow),
});

export const portfolioFit: Reader<PortfolioFitPage> = object<PortfolioFitPage>({
  limits,
  ratings,
  relativeValue,
  scatter,
  strips,
});

/** A value and its text are `null` together; the words say which pair. */
function checkPair(
  value: number | null,
  shown: string | null,
  where: string,
  noun: string,
  range: string | null,
): void {
  if (value === null) {
    if (shown !== null) fail(where, `expected null beside a missing ${noun}`);
    return;
  }
  if (shown === null) fail(where, `expected a text beside a present ${noun}`);
  if (range !== null) fail(where.replace(/Text$/, ""), range);
}

function checkLimits(l: Limits, path: string): void {
  if (l.head.length !== 3) {
    fail(`${path}.head`, "expected 3 headings: the label, the exposure and the limit");
  }
  atLeastOne(l.columns, `${path}.columns`, "column");
  distinct(l.columns, (c) => c.label, `${path}.columns`, "label", "column");
  l.columns.forEach((c, i) => {
    const where = at(`${path}.columns`, i);
    if (!(c.scaleMax > 0)) fail(`${where}.scaleMax`, "expected a number above zero");
    const range = `expected a position from 0 to the scale (${String(c.scaleMax)})`;
    for (const kind of ["exposure", "limit"] as const) {
      const value = c[kind];
      const out = value !== null && !(value >= 0 && value <= c.scaleMax);
      checkPair(value, c[`${kind}Text`], `${where}.${kind}Text`, kind, out ? range : null);
    }
    if (c.cells[0] !== c.exposureText) {
      fail(`${where}.cells[0]`, "expected the column's exposure text");
    }
    if (c.limitText === null) {
      if (c.cells[1] !== null) fail(`${where}.cells[1]`, "expected null beside a missing limit");
    } else if (c.cells[1] === null || c.limitText !== `limit ${c.cells[1]}`) {
      fail(`${where}.cells[1]`, "expected the column's limit text without its word");
    }
  });
}

function checkScatter(s: HoldingsScatter, path: string): void {
  if (s.head.length !== 3) {
    fail(`${path}.head`, "expected 3 headings: the label, the x and the y");
  }
  for (const which of ["x", "y"] as const) {
    const values = s[which].ticks.map((t) => t.value);
    if (values.length < 2 || values.some((v, i) => i > 0 && v <= (values[i - 1] ?? v))) {
      fail(`${path}.${which}.ticks`, "expected at least two ticks, rising");
    }
  }
  atLeastOne(s.points, `${path}.points`, "point");
  distinct(s.points, (p) => p.name, `${path}.points`, "name", "point");
  const seen = s.points.findIndex((p) => p.emphasis);
  const extra = s.points.findIndex((p, i) => p.emphasis && i !== seen);
  if (extra !== -1) {
    fail(`${at(`${path}.points`, extra)}.emphasis`, "expected at most one emphasised point");
  }
  if (s.points[seen]?.name === s.othersName) {
    fail(`${path}.othersName`, "expected a name the emphasised point does not have");
  }
  s.points.forEach((p, i) => {
    const where = at(`${path}.points`, i);
    for (const which of ["x", "y"] as const) {
      const ticks = s[which].ticks;
      const [low, high] = [ticks[0]?.value ?? 0, ticks[ticks.length - 1]?.value ?? 0];
      const value = p[which];
      const out = value !== null && !(value >= low && value <= high);
      const range = `expected a position from ${String(low)} to ${String(high)}`;
      checkPair(value, p[`${which}Text`], `${where}.${which}Text`, which, out ? range : null);
    }
    if (p.cells[0] !== p.xText) fail(`${where}.cells[0]`, "expected the point's x text");
    if (p.cells[1] !== p.yText) fail(`${where}.cells[1]`, "expected the point's y text");
  });
}

function checkStrips(s: HoldingsStrips, path: string, markersNeedRange = true): void {
  if (s.head.length === 0) fail(`${path}.head`, "expected a heading for the label column");
  atLeastOne(s.rows, `${path}.rows`, "row");
  distinct(s.rows, (r) => r.label, `${path}.rows`, "label", "row");
  const names = s.rows[0]?.markers.map((m) => m.name) ?? [];
  if (names.includes(s.rangeLabel)) {
    fail(`${path}.rangeLabel`, "expected a label no marker has");
  }
  s.rows.forEach((r, i) => {
    const where = at(`${path}.rows`, i);
    atLeastOne(r.markers, `${where}.markers`, "marker");
    distinct(r.markers, (m) => m.name, `${where}.markers`, "name", "marker in the row");
    if (r.markers.map((m) => m.name).join("\u0000") !== names.join("\u0000")) {
      fail(
        `${where}.markers[${String(r.markers.findIndex((m, j) => m.name !== names[j]))}].name`,
        "expected the names the first row's markers have, in order",
      );
    }
    if (!(r.axis.max > r.axis.min)) fail(`${where}.axis`, "expected a max above the min");
    const range = `expected a position from ${String(r.axis.min)} to ${String(r.axis.max)}`;
    const inside = (v: number) => v >= r.axis.min && v <= r.axis.max;
    if (r.range !== null) {
      if (!(r.range.low <= r.range.high)) {
        fail(`${where}.range`, "expected a low that is not above the high");
      }
      if (!inside(r.range.low) || !inside(r.range.high)) fail(`${where}.range`, range);
    }
    r.markers.forEach((m, j) => {
      const mark = at(`${where}.markers`, j);
      if (markersNeedRange && m.value !== null && r.range === null) {
        fail(`${mark}.value`, "expected null beside a missing range");
      }
      if (m.value !== null && !inside(m.value)) fail(`${mark}.value`, range);
      checkPair(m.value, m.text, `${mark}.text`, "value", null);
    });
    checkCells(r, s.head, where);
    // The cells end with the markers' texts, in order (the contract in types.ts).
    needCells(r, r.markers.length, where);
    r.markers.forEach((m, j) => {
      const column = r.cells.length - r.markers.length + j;
      const cellAt = `${where}.cells[${String(column)}]`;
      const cell = r.cells[column] ?? null;
      const what = `the text of marker ${String(j + 1)}, "${m.text ?? ""}"`;
      checkPresence(cell, m.text !== null, cellAt, "marker", what);
      if (cell !== m.text) fail(cellAt, `expected ${what}`);
    });
  });
}

/** Every rule the page and its charts enforce, so a slice that reads ok never throws there. */
export function checkPortfolioFit(page: PortfolioFitPage, path: string): void {
  checkLimits(page.limits, child(path, "limits"));
  const [first, second] = page.ratings.tiles;
  if (first.label === second.label) {
    fail(
      `${child(path, "ratings.tiles")}[1].label`,
      "expected a label the other tile does not have",
    );
  }
  checkScatter(page.scatter, child(path, "scatter"));
  checkStrips(page.strips, child(path, "strips"));
  const named = [page.limits, page.ratings, page.scatter, page.strips].map((c, i) => ({
    name: c.title,
    where: child(path, `${["limits", "ratings", "scatter", "strips"][i] ?? ""}.title`),
  }));
  named.forEach((item, i) => {
    if (named.findIndex((other) => other.name === item.name) !== i) {
      fail(item.where, "expected a name no other trace control on the page has");
    }
  });
}
