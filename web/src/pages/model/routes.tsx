// The model page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /model/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().model)`. Edit only this folder and fixtures/model.json.
import type { Route } from "../route-table";
import { RunsIndexPage } from "./RunsIndexPage";

export { readSlice } from "./slice/read";

export const routes: readonly Route[] = [
  {
    path: "/model/runs",
    home: "/model/runs",
    layout: "bleed",
    title: "Financial models",
    render: () => <RunsIndexPage />,
  },
];
