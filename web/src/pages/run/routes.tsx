// The run page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /run/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().run)`. Edit only this folder and fixtures/run.json.
import type { Route, SliceResult } from "../route-table";

type RunSlice = never;

export const routes: readonly Route[] = [];

export function readSlice(): SliceResult<RunSlice> {
  // No slice is read yet; the first page adds a `source: unknown` parameter and the slice type.
  return { kind: "absent" };
}
