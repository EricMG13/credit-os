// A worked example of how a page group adds a page, with a made-up group: declared route, params
// from its fixture, matched, slice read, rendered. Nothing here ships in the four real groups.
import { render, screen } from "@testing-library/react";
import { fillParams, pathsIn } from "../../scripts/route-paths.mjs";
import { App } from "../App";
import type { LoadResult } from "../data";
import { routeTable, matchRoute, type RouteTable, type SliceResult } from "./route-table";
import { useSource } from "./source";

type Summary = { headline: string };

function readSummary(source: unknown): SliceResult<Summary> {
  if (source === undefined) return { kind: "absent" };
  if (typeof source === "object" && source !== null && "headline" in source) {
    const headline = source.headline;
    if (typeof headline === "string") return { kind: "ok", data: { headline } };
  }
  return { kind: "invalid", reason: "the summary has no headline" };
}

function SummaryPage({ issuer }: { issuer: string }) {
  const slice = readSummary(useSource().model);
  return (
    <p>
      {issuer}: {slice.kind === "ok" ? slice.data.headline : "no summary"}
    </p>
  );
}

const GROUP_FILE = `
  { path: "/model/:issuer/summary", title: "Summary", render: renderSummary },
  { path: "/model/about", title: "About", render: renderAbout },
`;

const FIXTURE = JSON.parse(`{
  "slice": { "headline": "Leverage is falling" },
  "params": { "/model/:issuer/summary": [{ "issuer": "acme corp" }, { "issuer": "b/c" }] }
}`) as { slice: unknown; params: Record<string, Record<string, string>[]> };

const table: RouteTable = {
  routes: [
    {
      path: "/model/:issuer/summary",
      title: "Summary",
      render: (params) => <SummaryPage issuer={params["issuer"] ?? ""} />,
    },
    { path: "/model/about", title: "About", render: () => <p>About the model</p> },
  ],
  readers: { ...routeTable.readers, model: readSummary },
};

function ok(model: unknown): LoadResult {
  return { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], model } };
}

function show(hash: string, result: LoadResult, shown: RouteTable = table) {
  window.location.hash = `#${hash}`;
  return render(<App result={result} table={shown} />);
}

describe("a page group's path through the scaffolding", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("visits every declared path with the fixture's parameters", () => {
    const declared = pathsIn(GROUP_FILE);
    expect(declared).toEqual(table.routes.map((r) => r.path));
    let visits = 0;
    for (const pattern of declared) {
      const sets = pattern.includes(":") ? (FIXTURE.params[pattern] ?? []) : [{}];
      for (const set of sets) {
        const { hash } = fillParams(pattern, set);
        expect(matchRoute(hash, table.routes)?.params).toEqual(set);
        const view = show(hash, ok(FIXTURE.slice));
        expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
        view.unmount();
        visits += 1;
      }
    }
    expect(visits).toBe(3);
  });

  it("renders the page with the slice its own reader returned", () => {
    show("/model/acme%20corp/summary", ok(FIXTURE.slice));
    expect(screen.getByText("acme corp: Leverage is falling")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Summary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Model" })).toHaveAttribute("aria-current", "page");
  });

  it("still renders the page when the group's slice is absent", () => {
    show("/model/acme/summary", ok(undefined));
    expect(screen.getByText("acme: no summary")).toBeInTheDocument();
  });

  it("says the part could not be read, with the reader's reason, when the slice is invalid", () => {
    show("/model/acme/summary", ok({ nope: 1 }));
    expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
    expect(screen.getByText("the summary has no headline")).toBeInTheDocument();
    expect(screen.queryByText(/acme:/)).toBeNull();
    expect(screen.getByRole("navigation", { name: "Areas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Model" })).toHaveAttribute("aria-current", "page");
  });

  it.each([
    [{ kind: "missing" }, "Library data is missing"],
    [{ kind: "newer", schema: "credit-os-data/2" }, "This library was written by a newer version"],
  ] as const)("shows the state of %j, not the route", (result, words) => {
    show("/model/about", result);
    expect(screen.getByText(words)).toBeInTheDocument();
    expect(screen.queryByText("About the model")).toBeNull();
  });

  it("reads an unknown first segment as the library's area", () => {
    const odd: RouteTable = {
      routes: [{ path: "/elsewhere/page", title: "Elsewhere", render: () => <p>odd page</p> }],
      readers: {
        ...routeTable.readers,
        library: () => ({ kind: "invalid", reason: "library reader was asked" }),
      },
    };
    show("/elsewhere/page", ok(undefined), odd);
    expect(screen.getByText("library reader was asked")).toBeInTheDocument();
  });
});
