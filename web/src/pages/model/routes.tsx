// The model page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /model/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().model)`. Edit only this folder and fixtures/model.json.
import type { Route, SliceResult } from "../route-table";

type ModelSlice = never;

export const routes: readonly Route[] = [];

export function readSlice(): SliceResult<ModelSlice> {
  // No slice is read yet; the first page adds a `source: unknown` parameter and the slice type.
  return { kind: "absent" };
}
