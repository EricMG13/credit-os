// The run pages' slice: the types delivery (3B) and the service (5C) write to, and the reader
// that validates a whole slice by hand. The first failure wins and names its path.
import type { SliceResult } from "../route-table";
import { Invalid, fail, list, obj } from "./slice-read";
import { type StartDraft, draft } from "./slice-start";

export type { Readiness, Row, StartDraft } from "./slice-start";
export type RunSlice = { drafts: StartDraft[] };

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
