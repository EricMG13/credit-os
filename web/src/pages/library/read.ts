import { STATUS_SETS } from "@/components/status/sets";
import type { SliceResult } from "../route-table";
import type {
  Cell,
  HomeCard,
  Issuer,
  IssuerCard,
  LibraryHome,
  LibrarySlice,
  Measure,
  MeasureKey,
  MeasureSpec,
  RunState,
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
      return { label: str(b, "label", itemPath), min, max };
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

function readIssuer(value: unknown, path: string): Issuer {
  const i = rec(value, path);
  return { id: str(i, "id", path), name: str(i, "name", path) };
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
