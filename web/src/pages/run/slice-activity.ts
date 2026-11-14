// The Run activity part of the slice: its types and reader.
import {
  type Bar,
  type Obj,
  bar,
  fail,
  list,
  obj,
  oneOf,
  orNull,
  str,
  strOrNull,
} from "./slice-read";

const RUN_STATES = [
  "Queued",
  "Running",
  "Finished",
  "Failed",
  "Capped",
  "Rejected",
  "Interrupted",
] as const;
const MODULE_WORDS = [
  "Queued",
  "Running",
  "Finished",
  "Interrupted",
  "Not assessable",
  "Not run",
] as const;
type RunState = (typeof RUN_STATES)[number];
type ModuleWord = (typeof MODULE_WORDS)[number];
type Link = { label: string; href: string }; // href starts with "#/"
type RunAlert = { title: string; text: string; action: Link; alt: Link | null };
type Module = { name: string; state: ModuleWord; detail: string | null };
type ModuleStep =
  | ({ kind: "module" } & Module)
  | { kind: "group"; title: string; state: ModuleWord; showAll: string; modules: Module[] };
type ActivityLine = {
  who: string;
  time: string;
  text: string;
  state: RunState | "Not assessable";
};
type Figure = { value: string | null; bar: Bar }; // null draws "n.a."
type RunRecord = {
  kind: "run";
  id: string;
  issuer: string;
  state: RunState;
  labels: string[];
  line: string | null;
  alert: RunAlert | null;
  open: Link | null;
  spend: Figure;
  finished: Figure;
  elapsed: { value: string | null; note: string };
  modules:
    | { kind: "steps"; steps: ModuleStep[] }
    | { kind: "starting"; label: string } // live, no module has reported
    | { kind: "none"; title: string; text: string }; // rejected: nothing ran
  feed: ActivityLine[];
};
export type ActivityRecord =
  | RunRecord
  | { kind: "none"; id: string } // nothing has been started
  | { kind: "unreadable"; id: string; issuer: string; labels: string[]; alert: RunAlert };

// A module code (CP-3) stays off these pages: every string is checked where it is read.
const noCode = (v: string, at: string): string =>
  /\bCP-\d/.test(v) ? fail(at, "no module code") : v;
const text = (o: Obj, key: string, path: string): string =>
  noCode(str(o, key, path), `${path}.${key}`);
const textOrNull = (o: Obj, key: string, path: string): string | null => {
  const v = strOrNull(o, key, path);
  return v === null ? v : noCode(v, `${path}.${key}`);
};
const texts = (o: Obj, key: string, path: string): string[] =>
  list(o, key, path, (v, p) => (typeof v === "string" ? noCode(v, p) : fail(p, "a string")));

const link = (v: unknown, path: string): Link => {
  const o = obj(v, path);
  const href = text(o, "href", path);
  if (!href.startsWith("#/")) fail(`${path}.href`, 'an address starting with "#/"');
  return { label: text(o, "label", path), href };
};
const alert = (v: unknown, path: string): RunAlert => {
  const o = obj(v, path);
  return {
    title: text(o, "title", path),
    text: text(o, "text", path),
    action: link(o.action, `${path}.action`),
    alt: orNull(o, "alt", path, link),
  };
};
const figure = (v: unknown, path: string): Figure => {
  const o = obj(v, path);
  const value = textOrNull(o, "value", path);
  const b = bar(o.bar, `${path}.bar`);
  return { value, bar: { ...b, label: noCode(b.label, `${path}.bar.label`) } };
};
const line = (v: unknown, path: string): ActivityLine => {
  const o = obj(v, path);
  return {
    who: text(o, "who", path),
    time: text(o, "time", path),
    text: text(o, "text", path),
    state: oneOf(o, "state", path, [...RUN_STATES, "Not assessable"] as const),
  };
};
// A live run (Queued, Running) holds no "Not run" module; an ended run holds no live one.
const wordFor =
  (state: RunState) =>
  (o: Obj, path: string): ModuleWord => {
    const word = oneOf(o, "state", path, MODULE_WORDS);
    const live = state === "Queued" || state === "Running";
    if (live && word === "Not run") fail(`${path}.state`, "a module word a live run can carry");
    if (!live && (word === "Queued" || word === "Running"))
      fail(`${path}.state`, "a module word an ended run can carry");
    return word;
  };
const moduleOf =
  (state: RunState) =>
  (v: unknown, path: string): Module => {
    const o = obj(v, path);
    return {
      name: text(o, "name", path),
      state: wordFor(state)(o, path),
      detail: textOrNull(o, "detail", path),
    };
  };
const stepOf =
  (state: RunState) =>
  (v: unknown, path: string): ModuleStep => {
    const o = obj(v, path);
    const module = moduleOf(state);
    if (oneOf(o, "kind", path, ["module", "group"] as const) === "module")
      return { kind: "module", ...module(o, path) };
    const members = list(o, "modules", path, (m, p) => {
      const mo = obj(m, p);
      if ("kind" in mo || "modules" in mo) fail(p, "a plain module, not a group");
      return module(mo, p);
    });
    if (members.length === 0) fail(`${path}.modules`, "a non-empty list");
    return {
      kind: "group",
      title: text(o, "title", path),
      state: wordFor(state)(o, path),
      showAll: text(o, "showAll", path),
      modules: members,
    };
  };

function modules(o: Obj, state: RunState, path: string): RunRecord["modules"] {
  const m = obj(o.modules, `${path}.modules`);
  const at = `${path}.modules`;
  switch (oneOf(m, "kind", at, ["steps", "starting", "none"] as const)) {
    case "steps":
      return { kind: "steps", steps: list(m, "steps", at, stepOf(state)) };
    case "starting":
      if (state !== "Running") fail(`${at}.kind`, "starting only in a Running run");
      return { kind: "starting", label: text(m, "label", at) };
    case "none":
      if (state !== "Rejected") fail(`${at}.kind`, "none only in a Rejected run");
      return { kind: "none", title: text(m, "title", at), text: text(m, "text", at) };
  }
}

export function activity(v: unknown, path: string): ActivityRecord {
  const o = obj(v, path);
  const id = text(o, "id", path);
  switch (oneOf(o, "kind", path, ["run", "none", "unreadable"] as const)) {
    case "none":
      return { kind: "none", id };
    case "unreadable":
      return {
        kind: "unreadable",
        id,
        issuer: text(o, "issuer", path),
        labels: texts(o, "labels", path),
        alert: alert(o.alert, `${path}.alert`),
      };
    case "run": {
      const state = oneOf(o, "state", path, RUN_STATES);
      const elapsed = obj(o.elapsed, `${path}.elapsed`);
      return {
        kind: "run",
        id,
        issuer: text(o, "issuer", path),
        state,
        labels: texts(o, "labels", path),
        line: textOrNull(o, "line", path),
        alert: orNull(o, "alert", path, alert),
        open: orNull(o, "open", path, link),
        spend: figure(o.spend, `${path}.spend`),
        finished: figure(o.finished, `${path}.finished`),
        elapsed: {
          value: textOrNull(elapsed, "value", `${path}.elapsed`),
          note: text(elapsed, "note", `${path}.elapsed`),
        },
        modules: modules(o, state, path),
        feed: list(o, "feed", path, line),
      };
    }
  }
}
