// The signal page group. Add a page as a route object below with a literal `path: "/…"` property
// written in this file; every path starts with /signal/. scripts/route-paths.mjs reads these paths
// to visit each in a browser, and a test fails if it cannot see one. A page reads its data with
// `readSlice(useSource().signal)`. Edit only this folder and fixtures/signal.json.
import type { ReactElement } from "react";
import type { Route } from "../route-table";
import { SignalPage, type SignalPageKind } from "./SignalPage";

export { readSlice } from "./slice";

function page(kind: SignalPageKind) {
  return (params: Record<string, string>): ReactElement => (
    <SignalPage kind={kind} params={params} />
  );
}

export const routes: readonly Route[] = [
  {
    path: "/signal/:scene/feed/:view",
    home: "/signal/main/feed/for-you",
    layout: "bleed",
    title: "Signal",
    render: page("feed"),
  },
  { path: "/signal/:scene/topic/:topic", layout: "bleed", title: "Signal", render: page("topic") },
  { path: "/signal/:scene/group/:group", layout: "bleed", title: "Signal", render: page("group") },
  {
    path: "/signal/:scene/group/:group/thread/:thread",
    layout: "bleed",
    title: "Signal",
    render: page("thread"),
  },
  {
    path: "/signal/:scene/digest/:digest",
    layout: "bleed",
    title: "Signal",
    render: page("digest"),
  },
  {
    path: "/signal/:scene/settings/:section",
    layout: "bleed",
    title: "Signal",
    render: page("settings"),
  },
];
