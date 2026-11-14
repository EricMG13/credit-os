import { readFileSync } from "node:fs";
import path from "node:path";
import {
  declaredPaths,
  declaresHome,
  fillParams,
  homesIn,
  pathsIn,
} from "../../scripts/route-paths.mjs";
import { SLICE_KEYS } from "../data";
import { areaOf, homeProblems, matchRoute, routeTable, type Route } from "./route-table";

function route(pathPattern: string): Route {
  return { path: pathPattern, title: pathPattern, render: () => null as never };
}

describe("matchRoute", () => {
  const routes = [route("/library/:issuer/:run/overview"), route("/model/about"), route("/x")];
  const overview = "/library/:issuer/:run/overview";

  it.each([
    ["/library/tdg/r1/overview", overview, { issuer: "tdg", run: "r1" }],
    ["/library/tdg/r1/overview/", overview, { issuer: "tdg", run: "r1" }],
    ["/model/about/", "/model/about", {}],
    ["/library/a%20b/r%2F1/overview", overview, { issuer: "a b", run: "r/1" }],
  ])("matches %s, ignoring one trailing slash and decoding segments", (hash, pattern, params) => {
    const found = matchRoute(hash, routes);
    expect(found?.route.path).toBe(pattern);
    expect(found?.params).toEqual(params);
  });

  it.each([
    ["an unknown path", "/library/tdg/r1/changes"],
    ["another unknown path", "/nowhere"],
    ["the empty hash", ""],
    ["a second trailing slash", "/model/about//"],
    ["an empty parameter segment", "/library//r1/overview"],
    ["a malformed escape", "/library/%E0%A4%A/r1/overview"],
    ["a query string", "/x?a=1"],
    ["a longer path", "/x/y"],
  ])("returns null for %s", (_, hash) => {
    expect(matchRoute(hash, routes)).toBeNull();
  });

  it("lets the first matching route win", () => {
    const first = route("/a/:one");
    expect(matchRoute("/a/v", [first, route("/a/:two")])?.route).toBe(first);
  });

  it("does not treat a name from Object.prototype as a parameter value store", () => {
    const found = matchRoute("/a/constructor", [route("/a/:toString")]);
    expect(found?.params).toEqual({ toString: "constructor" });
    expect(Object.getPrototypeOf(found?.params)).toBeNull();
  });
});

describe("pathsIn", () => {
  it("finds literal paths in order and skips comments", () => {
    const source = [
      '// every route is written with a literal path: "/not-this"',
      '/* path: "/nor-this" */',
      "export const routes = [",
      '  { path: "/model/:issuer/summary", title: "Summary", render: () => null },',
      '  { path: "/model/about", title: "About", render: () => null },',
      "];",
    ].join("\n");
    expect(pathsIn(source)).toEqual(["/model/:issuer/summary", "/model/about"]);
  });
});

describe("declaresHome", () => {
  it("sees a home property and skips comments", () => {
    expect(declaresHome('{ path: "/run/a", home: "/run/a", title: "A" }')).toBe(true);
    expect(declaresHome('// home: "/run/a"\n{ path: "/run/a" }')).toBe(false);
    expect(declaresHome("export const routes = [];")).toBe(false);
  });
});

describe("homesIn", () => {
  it("lists the double-quoted literal homes, in order, and only those", () => {
    expect(homesIn('{ home: "/run/a" }, { path: "/run/b", home: "/run/b" }')).toEqual([
      "/run/a",
      "/run/b",
    ]);
    expect(homesIn('// home: "/run/a"\n{ path: "/run/a" }')).toEqual([]);
  });

  it.each([
    ["a constant", "{ home: HOME }"],
    ["a single-quoted string", "{ home: '/run/a' }"],
    ["a template string", "{ home: `/run/a` }"],
    ["a quoted key", '{ "home": "/run/a" }'],
  ])("does not see %s, so the per-group check below fails for it", (_, source) => {
    expect(homesIn(source)).toEqual([]);
    expect(declaresHome(source)).toBe(false);
  });
});

describe("fillParams", () => {
  it("replaces the whole segment after a colon, as matchRoute reads it", () => {
    const pattern = "/library/:issuer-id/:run_2/overview";
    const { hash, missing } = fillParams(pattern, { "issuer-id": "a b", run_2: "r1" });
    expect(hash).toBe("/library/a%20b/r1/overview");
    expect(missing).toEqual([]);
    expect(matchRoute(hash, [route(pattern)])?.params).toEqual({ "issuer-id": "a b", run_2: "r1" });
    expect(fillParams(pattern, { run_2: "r1" }).missing).toEqual(["issuer-id"]);
  });
});

describe("the real page groups", () => {
  it.each(SLICE_KEYS)("%s: the script sees exactly the routes the module declares", (group) => {
    const dir = path.join(import.meta.dirname, group);
    const wrong = declaredPaths(dir).filter((p) => !p.startsWith(`/${group}/`));
    expect(wrong, `every path in ${group}/routes.tsx must start with /${group}/`).toEqual([]);
    const declared = routeTable.routes.filter((r) => r.path.split("/")[1] === group);
    expect(declaredPaths(dir)).toEqual(declared.map((r) => r.path));
  });

  it.each(SLICE_KEYS)(
    "%s: every home is a double-quoted literal in routes.tsx, so the script sees it",
    (group) => {
      const source = readFileSync(path.join(import.meta.dirname, group, "routes.tsx"), "utf8");
      const declared = routeTable.routes
        .filter((r) => r.path.split("/")[1] === group)
        .flatMap((r) => (r.home === undefined ? [] : [r.home]));
      expect(homesIn(source), `home in ${group}/routes.tsx must be a "…" literal`).toEqual(
        declared,
      );
      expect(declaresHome(source)).toBe(declared.length > 0);
    },
  );

  it("every route belongs to a group folder", () => {
    const seen = SLICE_KEYS.flatMap((group) =>
      declaredPaths(path.join(import.meta.dirname, group)),
    );
    expect(seen).toEqual(routeTable.routes.map((r) => r.path));
  });

  it.each(SLICE_KEYS)(
    "%s: the reader reports an absent slice for a library without it",
    (group) => {
      expect(routeTable.readers[group](undefined)).toEqual({ kind: "absent" });
    },
  );
});

describe("declared homes", () => {
  const sig = "/signal/:space/feed/:tab";
  const withHome = (path: string, home: string) => ({ ...route(path), home });

  it.each([
    ["a concrete address its path matches", withHome(sig, "/signal/main/feed/for-you"), 0],
    ["a route with no home", route(sig), 0],
    ["a home with a : segment", withHome(sig, "/signal/:space/feed/for-you"), 1],
    ["a home its path does not match", withHome(sig, "/signal/main/other"), 1],
    ["a home another route matches first", withHome("/signal/b/c", "/signal/b/c"), 1],
    ["a home outside the group", withHome("/signal/x", "/model/x"), 1],
    ["a home with a query", withHome("/signal/:q", "/signal/a?b"), 1],
    ["a home with an encoded colon", withHome("/signal/:q", "/signal/a%3Ab"), 0],
  ])("%s: %i problem(s)", (_, candidate, count) => {
    const earlier = candidate.path === "/signal/b/c" ? [route("/signal/:p/c")] : [];
    expect(homeProblems([...earlier, candidate])).toHaveLength(count);
  });

  it("names the group when a home leaves it though its route matches", () => {
    const stray = withHome("/:group/x", "/signal/x");
    expect(areaOf(stray.path)).toBe("library");
    expect(homeProblems([stray])).toEqual(["/:group/x: home /signal/x is outside /library/"]);
  });

  it("flags a second home in one group, and only in the same group", () => {
    const first = withHome("/signal/a", "/signal/a");
    const second = withHome("/signal/b", "/signal/b");
    expect(homeProblems([first, second])).toEqual([
      "/signal/b: group signal already has a home, /signal/a",
    ]);
    expect(homeProblems([first, withHome("/run/b", "/run/b")])).toEqual([]);
  });

  it("finds no problem in the real route table", () => {
    expect(homeProblems(routeTable.routes)).toEqual([]);
  });
});
