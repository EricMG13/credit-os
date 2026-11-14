// The library page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /library/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().library)`. Edit only this folder and fixtures/library.json.
import type { Route } from "../route-table";
import { Changes } from "./Changes";
import { Evidence } from "./Evidence";
import { History } from "./History";
import { Home } from "./Home";
import { ModulePage } from "./Module";
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
  {
    path: "/library/:issuer/:run/modules",
    layout: "bleed",
    title: PAGE_NAME.modules,
    render: (params) => (
      <ModulePage issuer={params["issuer"]} run={params["run"]} module={undefined} />
    ),
  },
  {
    path: "/library/:issuer/:run/modules/:module",
    layout: "bleed",
    title: PAGE_NAME.modules,
    render: (params) => (
      <ModulePage issuer={params["issuer"]} run={params["run"]} module={params["module"]} />
    ),
  },
  {
    path: "/library/:issuer/:run/evidence",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => <Evidence issuer={params["issuer"]} run={params["run"]} page="summary" />,
  },
  {
    path: "/library/:issuer/:run/evidence/summary",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => <Evidence issuer={params["issuer"]} run={params["run"]} page="summary" />,
  },
  {
    path: "/library/:issuer/:run/evidence/sources",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => <Evidence issuer={params["issuer"]} run={params["run"]} page="sources" />,
  },
  {
    path: "/library/:issuer/:run/evidence/trace",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => <Evidence issuer={params["issuer"]} run={params["run"]} page="trace" />,
  },
  {
    path: "/library/:issuer/:run/evidence/trace/:item",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => (
      <Evidence issuer={params["issuer"]} run={params["run"]} page="trace" item={params["item"]} />
    ),
  },
  {
    path: "/library/:issuer/:run/evidence/gaps",
    layout: "bleed",
    title: PAGE_NAME.evidence,
    render: (params) => <Evidence issuer={params["issuer"]} run={params["run"]} page="gaps" />,
  },
];
