// The Run start part of the slice: its types and reader.
import {
  type Bar,
  bar,
  fail,
  list,
  obj,
  oneOf,
  orNull,
  str,
  strOrNull,
  strings,
} from "./slice-read";

export type Row = { label: string; value: string | null }; // null draws "n.a."
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
    progress: orNull(o, "progress", path, bar),
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
export function draft(v: unknown, path: string): StartDraft {
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
  const step = oneOf(o, "step", path, STEPS);
  if (step !== "started" && base.next === null && base.nextBlocked === null)
    fail(`${path}.nextBlocked`, "a reason when next is null");
  switch (step) {
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
      const groups = list(o, "groups", path, group);
      const names = new Set<string>();
      groups.forEach((g, i) => {
        if (names.has(g.name))
          fail(`${path}.groups[${String(i)}].name`, "a name no other group uses");
        names.add(g.name);
      });
      return { ...base, step: "confirm", groups };
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
