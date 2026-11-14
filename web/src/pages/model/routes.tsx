// The model page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /model/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().model)`. Edit only this folder and fixtures/model.json.
import type { Route } from "../route-table";
import { FrontPage } from "./FrontPage";
import { LimitationsPage } from "./LimitationsPage";
import { RunsIndexPage } from "./RunsIndexPage";
import { StatementsPage } from "./StatementsPage";

export { readSlice } from "./slice/read";

export const routes: readonly Route[] = [
  {
    path: "/model/runs",
    home: "/model/runs",
    layout: "bleed",
    title: "Financial models",
    render: () => <RunsIndexPage />,
  },
  {
    path: "/model/:issuer/:run/front",
    layout: "bleed",
    title: "Front page",
    render: (params) => <FrontPage params={params} />,
  },
  {
    path: "/model/:issuer/:run/statements",
    layout: "bleed",
    title: "Model",
    render: (params) => <StatementsPage params={params} />,
  },
  {
    path: "/model/:issuer/:run/limitations",
    layout: "bleed",
    title: "Limitations",
    render: (params) => <LimitationsPage params={params} />,
  },
];
