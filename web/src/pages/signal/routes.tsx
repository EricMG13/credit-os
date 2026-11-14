// The signal page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /signal/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().signal)`. Edit only this folder and fixtures/signal.json.
import type { Route } from "../route-table";

export { readSlice } from "./slice";

export const routes: readonly Route[] = [];
