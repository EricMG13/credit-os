import {
  addressOrNull,
  address,
  arrayOf,
  at,
  atLeastOne,
  checkCells,
  checkPresence,
  child,
  chartInfo as info,
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
  AnalysisLimitations,
  AnalysisPage,
  Finding,
  Headroom,
  HeadroomRow,
  Measure,
  Passage,
  SegmentRow,
  Segments,
} from "./types";

const cells = arrayOf(textOrNull);

const finding = object<Finding>({ number: text, title: text, text, trace: addressOrNull });
const measure = object<Measure>({
  label: text,
  value: textOrNull,
  delta: text,
  text,
  trace: addressOrNull,
});
export const passage = object<Passage>({ title: text, text, trace: addressOrNull });
const headroomRow = object<HeadroomRow>({
  label: text,
  sub: text,
  value: numOrNull,
  target: num,
  axisMax: num,
  text: textOrNull,
  cells,
});
const headroom = object<Headroom>({ ...info, head: arrayOf(text), rows: arrayOf(headroomRow) });
const segmentRow = object<SegmentRow>({
  label: text,
  from: numOrNull,
  to: numOrNull,
  text,
  cells,
});
const segments = object<Segments>({
  ...info,
  names: pairOf(text),
  axis: object({ min: num, max: num }),
  head: arrayOf(text),
  rows: arrayOf(segmentRow),
});
const limitations = object<AnalysisLimitations>({
  count: text,
  linkText: text,
  href: address,
  items: arrayOf(object({ title: text, text, trace: addressOrNull })),
});

export const analysis: Reader<AnalysisPage> = object<AnalysisPage>({
  findings: arrayOf(finding),
  measures: object({ period: text, stats: arrayOf(measure) }),
  headroom,
  segments,
  contrary: passage,
  watch: passage,
  limitations,
});

function checkHeadroom(h: Headroom, path: string): void {
  if (h.head.length === 0) fail(`${path}.head`, "expected a heading for the label column");
  atLeastOne(h.rows, `${path}.rows`, "row");
  distinct(h.rows, (r) => r.label, `${path}.rows`, "label", "row");
  h.rows.forEach((r, i) => {
    const where = at(`${path}.rows`, i);
    if (!(r.axisMax > 0)) fail(`${where}.axisMax`, "expected a number above zero");
    const range = `expected a position from 0 to the axis max (${String(r.axisMax)})`;
    if (r.value !== null && !(r.value >= 0 && r.value <= r.axisMax)) fail(`${where}.value`, range);
    if (!(r.target >= 0 && r.target <= r.axisMax)) fail(`${where}.target`, range);
    if (r.value === null && r.text !== null) {
      fail(`${where}.text`, "expected null beside a missing value");
    }
    if (r.value !== null && r.text === null) {
      fail(`${where}.text`, "expected a text beside a present value");
    }
    checkCells(r, h.head, where);
    // The first cell is the value's text; the row's text starts with it ("5.9x of 7.0x").
    needCells(r, 1, where);
    const cell = r.cells[0] ?? null;
    checkPresence(cell, r.value !== null, `${where}.cells[0]`, "value", "the value's text");
    if (r.text !== null && cell !== r.text && !r.text.startsWith(`${cell ?? ""} `)) {
      fail(`${where}.cells[0]`, `expected the value's text, which "${r.text}" starts with`);
    }
  });
}

function checkSegments(s: Segments, path: string): void {
  if (s.names[0] === s.names[1]) fail(`${path}.names`, "expected two different names");
  if (!(s.axis.max > s.axis.min)) fail(`${path}.axis`, "expected a max above the min");
  if (s.head.length === 0) fail(`${path}.head`, "expected a heading for the label column");
  atLeastOne(s.rows, `${path}.rows`, "row");
  distinct(s.rows, (r) => r.label, `${path}.rows`, "label", "row");
  s.rows.forEach((r, i) => {
    const where = at(`${path}.rows`, i);
    const range = `expected a position from ${String(s.axis.min)} to ${String(s.axis.max)}`;
    for (const end of ["from", "to"] as const) {
      const v = r[end];
      if (v !== null && !(v >= s.axis.min && v <= s.axis.max)) fail(`${where}.${end}`, range);
    }
    if (r.from === null && r.to === null) fail(where, "expected at least one end present");
    // The cells are the earlier text, then the later; the row's text joins them with " to ".
    checkCells(r, s.head, where);
    needCells(r, 2, where);
    const [earlier, later] = [r.cells[0] ?? null, r.cells[1] ?? null];
    checkPresence(
      earlier,
      r.from !== null,
      `${where}.cells[0]`,
      "earlier mark",
      "the earlier text",
    );
    checkPresence(later, r.to !== null, `${where}.cells[1]`, "later mark", "the later text");
    if (r.text !== `${earlier ?? "n.a."} to ${later ?? "n.a."}`) {
      fail(
        `${where}.text`,
        'expected the earlier and later cells joined by " to ", n.a. where missing',
      );
    }
  });
}

/** Every rule the page and its two charts enforce, so a slice that reads ok never throws there. */
export function checkAnalysis(page: AnalysisPage, path: string): void {
  atLeastOne(page.findings, child(path, "findings"), "finding");
  distinct(page.findings, (f) => f.number, child(path, "findings"), "number", "finding");
  atLeastOne(page.measures.stats, child(path, "measures.stats"), "measure");
  distinct(page.measures.stats, (m) => m.label, child(path, "measures.stats"), "label", "measure");
  checkHeadroom(page.headroom, child(path, "headroom"));
  checkSegments(page.segments, child(path, "segments"));
  atLeastOne(page.limitations.items, child(path, "limitations.items"), "limitation");
  distinct(
    page.limitations.items,
    (l) => l.title,
    child(path, "limitations.items"),
    "title",
    "limitation",
  );
  checkTraceNames(page, path);
}

/** Every trace control is named by its item's text, so no two items on the page may share one. */
function checkTraceNames(page: AnalysisPage, path: string): void {
  const named: { name: string; where: string }[] = [
    ...page.findings.map((f, i) => ({
      name: f.title,
      where: `${at(child(path, "findings"), i)}.title`,
    })),
    ...page.measures.stats.map((m, i) => ({
      name: m.label,
      where: `${at(child(path, "measures.stats"), i)}.label`,
    })),
    { name: page.headroom.title, where: child(path, "headroom.title") },
    { name: page.segments.title, where: child(path, "segments.title") },
    { name: page.contrary.title, where: child(path, "contrary.title") },
    { name: page.watch.title, where: child(path, "watch.title") },
    ...page.limitations.items.map((l, i) => ({
      name: l.title,
      where: `${at(child(path, "limitations.items"), i)}.title`,
    })),
  ];
  named.forEach((item, i) => {
    if (named.findIndex((other) => other.name === item.name) !== i) {
      fail(item.where, "expected a name no other trace control on the page has");
    }
  });
}
