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
  object,
  oneOf,
  text,
  type Reader,
} from "./reader-kit";
import type {
  GapItem,
  LimitationsPage,
  Limitation,
  ModelRun,
  ModelSlice,
  RunHeader,
  RunLinks,
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
  limitations,
});
const run: Reader<ModelRun> = (value, path) => {
  const read = runFields(value, path);
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
