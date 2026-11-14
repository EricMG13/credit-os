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
  object,
  oneOf,
  orNull,
  text,
  textOrNull,
  yes,
  type Reader,
} from "./reader-kit";
import type {
  Fact,
  FrontPage,
  GapItem,
  LimitationsPage,
  Limitation,
  Metric,
  MetricValue,
  ModelRun,
  ModelSlice,
  RunHeader,
  RunLinks,
  Part,
  PartPage,
  RunState,
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

const runFields = object<ModelRun>({
  issuer: text,
  run: text,
  header,
  links,
  front,
  limitations,
});
const run: Reader<ModelRun> = (value, path) => {
  const read = runFields(value, path);
  checkFront(read.front, child(path, "front"));
  checkLimitations(read.limitations, child(path, "limitations"));
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
