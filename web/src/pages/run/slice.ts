// The run pages' slice: the types delivery (3B) and the service (5C) write to, and the reader
// that validates a whole slice by hand. The first failure wins and names its path.
import type { SliceResult } from "../route-table";

type Bar = { label: string; value: number; max: number }; // numbers place the fill only
type Row = { label: string; value: string | null }; // null draws "n.a."
const FILE_STATES = ["Uploading", "Read in full", "Read in part", "Unreadable"] as const;
type StartFile = {
  name: string;
  kind: string;
  size: string;
  state: (typeof FILE_STATES)[number];
  progress: Bar | null; // the bar under an uploading or fully read file
  reason: string | null; // the sentence for Read in part and Unreadable
};
type Purpose = { id: string; title: string; description: string; modules: string };
type Items = { count: string; items: string[] };
export type Readiness = { line: string; notMet: Items; met: Items; cap: Bar };
type DraftBase = {
  id: string;
  issuer: string;
  position: string; // "Step 1 of 5"
  previous: string | null; // sibling draft ids
  next: string | null;
  nextLabel: string; // "Next", "Approve summary", "Submit, spend up to USD 20.00"
  nextBlocked: string | null; // reason Next is unavailable
  readiness: Readiness;
};
type Confirm = { title: string; text: string; action: string; started: string };
export type StartDraft = DraftBase &
  (
    | { step: "documents"; files: StartFile[] }
    | { step: "purpose"; chosen: string | null; purposes: Purpose[] }
    | { step: "confirm"; groups: { name: string; rows: Row[] }[] }
    | { step: "context"; note: string }
    | { step: "start"; recap: Row[]; paid: { text: string; amount: string }; confirm: Confirm }
    | { step: "started"; title: string; text: string; cap: Bar; activity: string }
  );
export type RunSlice = { drafts: StartDraft[] };

class Invalid extends Error {}
const fail = (path: string, expected: string): never => {
  throw new Invalid(`${path}: expected ${expected}`);
};
type Obj = Record<string, unknown>;

function obj(v: unknown, path: string): Obj {
  if (typeof v !== "object" || v === null || Array.isArray(v)) return fail(path, "an object");
  return v as Obj;
}
function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  return typeof v === "string" ? v : fail(`${path}.${key}`, "a string");
}
function strOrNull(o: Obj, key: string, path: string): string | null {
  const v = o[key];
  return v === null || typeof v === "string" ? v : fail(`${path}.${key}`, "a string or null");
}
function list<T>(o: Obj, key: string, path: string, read: (v: unknown, p: string) => T): T[] {
  const v = o[key];
  if (!Array.isArray(v)) return fail(`${path}.${key}`, "a list");
  return v.map((item, i) => read(item, `${path}.${key}[${String(i)}]`));
}
function oneOf<T extends string>(o: Obj, key: string, path: string, words: readonly T[]): T {
  const v = o[key];
  return words.find((w) => w === v) ?? fail(`${path}.${key}`, `one of ${words.join(", ")}`);
}
function bar(v: unknown, path: string): Bar {
  const o = obj(v, path);
  const { value, max } = o;
  if (typeof max !== "number" || !Number.isFinite(max) || max <= 0)
    fail(`${path}.max`, "a number above 0");
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    value < 0 ||
    value > (max as number)
  ) {
    fail(`${path}.value`, "a number from 0 to max");
  }
  return { label: str(o, "label", path), value: value as number, max: max as number };
}
function barOrNull(o: Obj, key: string, path: string): Bar | null {
  const v = o[key];
  if (v === null) return null;
  if (typeof v !== "object" || Array.isArray(v)) return fail(`${path}.${key}`, "an object or null");
  return bar(v, `${path}.${key}`);
}
const strings = (o: Obj, key: string, path: string): string[] =>
  list(o, key, path, (v, p) => (typeof v === "string" ? v : fail(p, "a string")));
const row = (v: unknown, path: string): Row => {
  const o = obj(v, path);
  return { label: str(o, "label", path), value: strOrNull(o, "value", path) };
};
const items = (v: unknown, path: string): Items => {
  const o = obj(v, path);
  return { count: str(o, "count", path), items: strings(o, "items", path) };
};
const file = (v: unknown, path: string): StartFile => {
  const o = obj(v, path);
  return {
    name: str(o, "name", path),
    kind: str(o, "kind", path),
    size: str(o, "size", path),
    state: oneOf(o, "state", path, FILE_STATES),
    progress: barOrNull(o, "progress", path),
    reason: strOrNull(o, "reason", path),
  };
};
const purpose = (v: unknown, path: string): Purpose => {
  const o = obj(v, path);
  return {
    id: str(o, "id", path),
    title: str(o, "title", path),
    description: str(o, "description", path),
    modules: str(o, "modules", path),
  };
};
const readiness = (v: unknown, path: string): Readiness => {
  const o = obj(v, path);
  return {
    line: str(o, "line", path),
    notMet: items(o.notMet, `${path}.notMet`),
    met: items(o.met, `${path}.met`),
    cap: bar(o.cap, `${path}.cap`),
  };
};
function confirm(v: unknown, path: string): Confirm {
  const o = obj(v, path);
  return {
    title: str(o, "title", path),
    text: str(o, "text", path),
    action: str(o, "action", path),
    started: str(o, "started", path),
  };
}

const STEPS = ["documents", "purpose", "confirm", "context", "start", "started"] as const;
function draft(v: unknown, path: string): StartDraft {
  const o = obj(v, path);
  const base: DraftBase = {
    id: str(o, "id", path),
    issuer: str(o, "issuer", path),
    position: str(o, "position", path),
    previous: strOrNull(o, "previous", path),
    next: strOrNull(o, "next", path),
    nextLabel: str(o, "nextLabel", path),
    nextBlocked: strOrNull(o, "nextBlocked", path),
    readiness: readiness(o.readiness, `${path}.readiness`),
  };
  switch (oneOf(o, "step", path, STEPS)) {
    case "documents":
      return { ...base, step: "documents", files: list(o, "files", path, file) };
    case "purpose": {
      const purposes = list(o, "purposes", path, purpose);
      const seen = new Set<string>();
      purposes.forEach((p, i) => {
        if (seen.has(p.id))
          fail(`${path}.purposes[${String(i)}].id`, "an id no other purpose uses");
        seen.add(p.id);
      });
      const chosen = strOrNull(o, "chosen", path);
      if (chosen !== null && !purposes.some((p) => p.id === chosen)) {
        fail(`${path}.chosen`, "null or the id of one of its purposes");
      }
      return { ...base, step: "purpose", chosen, purposes };
    }
    case "confirm": {
      const group = (g: unknown, p: string) => {
        const go = obj(g, p);
        return { name: str(go, "name", p), rows: list(go, "rows", p, row) };
      };
      return { ...base, step: "confirm", groups: list(o, "groups", path, group) };
    }
    case "context":
      return { ...base, step: "context", note: str(o, "note", path) };
    case "start": {
      const paid = obj(o.paid, `${path}.paid`);
      return {
        ...base,
        step: "start",
        recap: list(o, "recap", path, row),
        paid: {
          text: str(paid, "text", `${path}.paid`),
          amount: str(paid, "amount", `${path}.paid`),
        },
        confirm: confirm(o.confirm, `${path}.confirm`),
      };
    }
    case "started":
      if (base.next !== null) fail(`${path}.next`, "null on a started draft");
      return {
        ...base,
        step: "started",
        title: str(o, "title", path),
        text: str(o, "text", path),
        cap: bar(o.cap, `${path}.cap`),
        activity: str(o, "activity", path),
      };
  }
}

function slice(source: unknown): RunSlice {
  const drafts = list(obj(source, "run"), "drafts", "run", draft);
  const ids = new Set<string>();
  drafts.forEach((d, i) => {
    if (ids.has(d.id)) fail(`run.drafts[${String(i)}].id`, "an id no other draft uses");
    ids.add(d.id);
  });
  drafts.forEach((d, i) => {
    const names = (key: string, id: string | null, nullable: boolean) => {
      if (id === null ? !nullable : !ids.has(id)) {
        const expected = "the id of a draft in this slice";
        fail(`run.drafts[${String(i)}].${key}`, nullable ? `null or ${expected}` : expected);
      }
    };
    names("previous", d.previous, true);
    names("next", d.next, true);
    if (d.step === "start") names("confirm.started", d.confirm.started, false);
  });
  return { drafts };
}

export function readSlice(source: unknown): SliceResult<RunSlice> {
  if (source === undefined) return { kind: "absent" };
  try {
    return { kind: "ok", data: slice(source) };
  } catch (e) {
    if (e instanceof Invalid) return { kind: "invalid", reason: e.message };
    throw e;
  }
}
