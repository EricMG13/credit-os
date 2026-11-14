// The library page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /library/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().library)`. Edit only this folder and fixtures/library.json.
import type { Route } from "../route-table";
import { History } from "./History";
import { Home } from "./Home";
import { Overview } from "./Overview";

export { readSlice } from "./read";

export const routes: readonly Route[] = [
  {
    path: "/library/home",
    home: "/library/home",
    layout: "bleed",
    title: "Library",
    render: () => <Home />,
  },
  {
    path: "/library/:issuer/history",
    layout: "bleed",
    title: "Report history",
    render: (params) => <History issuer={params["issuer"]} />,
  },
  {
    path: "/library/:issuer/:run/overview",
    layout: "bleed",
    title: "Overview",
    render: (params) => <Overview issuer={params["issuer"]} run={params["run"]} />,
  },
];
