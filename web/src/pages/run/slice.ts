// The run pages' slice: the types delivery (3B) and the service (5C) write to, and the reader
// that validates a whole slice by hand. The first failure wins and names its path.
import type { SliceResult } from "../route-table";
import { type ActivityRecord, activity } from "./slice-activity";
import { Invalid, fail, list, obj, strOrNull } from "./slice-read";
import { type StartDraft, draft } from "./slice-start";

export type { Readiness, Row, StartDraft } from "./slice-start";
export type RunSlice = { drafts: StartDraft[]; runs: ActivityRecord[]; current: string | null };

function unique(ids: string[], path: string, what: string): Set<string> {
  const seen = new Set<string>();
  ids.forEach((id, i) => {
    if (seen.has(id)) fail(`${path}[${String(i)}].id`, `an id no other ${what} uses`);
    seen.add(id);
  });
  return seen;
}

function slice(source: unknown): RunSlice {
  const root = obj(source, "run");
  const drafts = list(root, "drafts", "run", draft);
  const ids = unique(
    drafts.map((d) => d.id),
    "run.drafts",
    "draft",
  );
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
  const runs = list(root, "runs", "run", activity);
  const runIds = unique(
    runs.map((r) => r.id),
    "run.runs",
    "run",
  );
  const current = strOrNull(root, "current", "run");
  if (current !== null && !runIds.has(current))
    fail("run.current", "null or the id of a run in this slice");
  drafts.forEach((d, i) => {
    if (d.step === "started" && !runIds.has(d.activity))
      fail(`run.drafts[${String(i)}].activity`, "the id of a run in this slice");
  });
  return { drafts, runs, current };
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
