// The library page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /library/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().library)`. Edit only this folder and fixtures/library.json.
import type { Route } from "../route-table";
import { Changes } from "./Changes";
import { History } from "./History";
import { Home } from "./Home";
import { Overview } from "./Overview";
import { PAGE_NAME } from "./parts/PageTitle";

export { readSlice } from "./read";

export const routes: readonly Route[] = [
  {
    path: "/library/home",
    home: "/library/home",
    layout: "bleed",
    title: PAGE_NAME.home,
    render: () => <Home />,
  },
  {
    path: "/library/:issuer/history",
    layout: "bleed",
    title: PAGE_NAME.history,
    render: (params) => <History issuer={params["issuer"]} />,
  },
  {
    path: "/library/:issuer/:run/overview",
    layout: "bleed",
    title: PAGE_NAME.overview,
    render: (params) => <Overview issuer={params["issuer"]} run={params["run"]} />,
  },
  {
    path: "/library/:issuer/:run/changes",
    layout: "bleed",
    title: PAGE_NAME.changes,
    render: (params) => <Changes issuer={params["issuer"]} run={params["run"]} />,
  },
];
