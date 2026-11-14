// The run page group. Add a page by adding a route object below with a literal `path: "/…"`
// property written in this file: scripts/route-paths.mjs reads these paths to visit each one in
// a browser, and a test fails when it cannot see a route this array declares. A route's page
// reads its data with `readSlice(useSource().run)`. Edit only this folder and
// fixtures/run.json.
import type { Route, SliceResult } from "../route-table";

type RunSlice = never;

export const routes: readonly Route[] = [];

export function readSlice(): SliceResult<RunSlice> {
  // No slice is read yet. The group gives this reader a `source: unknown` parameter and its own
  // slice type when it adds its first page.
  return { kind: "absent" };
}
