// The run page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /run/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().run)`. Edit only this folder and fixtures/run.json.
import type { Route } from "../route-table";
import { ActivityPage } from "./activity/ActivityPage";
import { StartPage } from "./start/StartPage";

export { readSlice } from "./slice";

export const routes: readonly Route[] = [
  {
    path: "/run/start/:draft",
    title: "Start a run",
    render: (params) => <StartPage draft={params["draft"] ?? ""} />,
  },
  {
    path: "/run/activity",
    title: "Run activity",
    layout: "bleed",
    home: "/run/activity",
    render: () => <ActivityPage run={null} />,
  },
  {
    path: "/run/activity/:run",
    title: "Run activity",
    layout: "bleed",
    render: (params) => <ActivityPage run={params["run"] ?? ""} />,
  },
];
