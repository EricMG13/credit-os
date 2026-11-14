// The Run activity part of the slice: its types and reader.
import {
  type Bar,
  type Obj,
  bar,
  fail,
  id as idOf,
  list,
  nonEmpty,
  obj,
  oneOf,
  orNull,
  str,
  strOrNull,
  strings,
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
export type ModuleWord = (typeof MODULE_WORDS)[number];
type Link = { label: string; href: string }; // href starts with "#/"
type RunAlert = { title: string; text: string; action: Link; alt: Link | null };
type Module = { name: string; state: ModuleWord; detail: string | null };
export type ModuleStep =
  | ({ kind: "module" } & Module)
  | { kind: "group"; title: string; state: ModuleWord; showAll: string; modules: Module[] };
export type ActivityLine = {
  who: string;
  time: string;
  text: string;
  state: RunState | "Not assessable";
};
export type Figure =
  { value: string | null; bar: Bar } | { value: string | null; bar: null; note: string }; // a missing figure draws "n.a." and no bar
export type RunRecord = {
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

const link = (v: unknown, path: string): Link => {
  const o = obj(v, path);
  const label = str(o, "label", path);
  const href = str(o, "href", path);
  if (!href.startsWith("#/")) fail(`${path}.href`, 'an address starting with "#/"');
  return { label, href };
};
const alert = (v: unknown, path: string): RunAlert => {
  const o = obj(v, path);
  return {
    title: str(o, "title", path),
    text: str(o, "text", path),
    action: link(o.action, `${path}.action`),
    alt: orNull(o, "alt", path, link),
  };
};
const figure = (v: unknown, path: string): Figure => {
  const o = obj(v, path);
  const value = strOrNull(o, "value", path);
  if (o.bar === null) return { value, bar: null, note: str(o, "note", path) };
  if (value === null) fail(`${path}.bar`, "null when the value is null");
  return { value, bar: bar(o.bar, `${path}.bar`) };
};
const line = (v: unknown, path: string): ActivityLine => {
  const o = obj(v, path);
  return {
    who: str(o, "who", path),
    time: str(o, "time", path),
    text: str(o, "text", path),
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
      name: str(o, "name", path),
      state: wordFor(state)(o, path),
      detail: strOrNull(o, "detail", path),
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
    nonEmpty(members, `${path}.modules`);
    return {
      kind: "group",
      title: str(o, "title", path),
      state: wordFor(state)(o, path),
      showAll: str(o, "showAll", path),
      modules: members,
    };
  };

function modules(o: Obj, state: RunState, path: string): RunRecord["modules"] {
  const m = obj(o.modules, `${path}.modules`);
  const at = `${path}.modules`;
  switch (oneOf(m, "kind", at, ["steps", "starting", "none"] as const)) {
    case "steps":
      return { kind: "steps", steps: nonEmpty(list(m, "steps", at, stepOf(state)), `${at}.steps`) };
    case "starting":
      if (state !== "Running") fail(`${at}.kind`, "starting only in a Running run");
      return { kind: "starting", label: str(m, "label", at) };
    case "none":
      if (state !== "Rejected") fail(`${at}.kind`, "none only in a Rejected run");
      return { kind: "none", title: str(m, "title", at), text: str(m, "text", at) };
  }
}

const ALERT_WHEN = "Failed, Capped, Rejected or Interrupted";
const ALERTED: readonly RunState[] = ["Failed", "Capped", "Rejected", "Interrupted"];
const only = <T>(v: T | null, at: string, allowed: boolean, when: string): T | null =>
  v === null || allowed ? v : fail(at, `null unless the run is ${when}`);

export function activity(v: unknown, path: string): ActivityRecord {
  const o = obj(v, path);
  const kind = oneOf(o, "kind", path, ["run", "none", "unreadable"] as const);
  const id = idOf(o, "id", path);
  switch (kind) {
    case "none":
      return { kind: "none", id };
    case "unreadable":
      return {
        kind: "unreadable",
        id,
        issuer: str(o, "issuer", path),
        labels: strings(o, "labels", path),
        alert: alert(o.alert, `${path}.alert`),
      };
    case "run": {
      const state = oneOf(o, "state", path, RUN_STATES);
      const elapsed = obj(o.elapsed, `${path}.elapsed`);
      return {
        kind: "run",
        id,
        issuer: str(o, "issuer", path),
        state,
        labels: strings(o, "labels", path),
        line: strOrNull(o, "line", path),
        alert: only(
          orNull(o, "alert", path, alert),
          `${path}.alert`,
          ALERTED.includes(state),
          ALERT_WHEN,
        ),
        open: only(orNull(o, "open", path, link), `${path}.open`, state === "Finished", "Finished"),
        spend: figure(o.spend, `${path}.spend`),
        finished: figure(o.finished, `${path}.finished`),
        elapsed: {
          value: strOrNull(elapsed, "value", `${path}.elapsed`),
          note: str(elapsed, "note", `${path}.elapsed`),
        },
        modules: modules(o, state, path),
        feed: nonEmpty(list(o, "feed", path, line), `${path}.feed`),
      };
    }
  }
}
