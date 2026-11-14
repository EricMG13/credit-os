import { readFileSync } from "node:fs";
import path from "node:path";
import { declaredPaths, fillParams, pathsIn } from "../../scripts/route-paths.mjs";
import { SLICE_KEYS } from "../data";
import { matchRoute, routeTable, type Route } from "./route-table";

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
  it.each(SLICE_KEYS)("%s: routes.tsx states the path rule in its convention comment", (group) => {
    const text = readFileSync(path.join(import.meta.dirname, group, "routes.tsx"), "utf8");
    expect(text).toContain(`every path starts with /${group}/`);
  });

  it.each(SLICE_KEYS)("%s: the script sees exactly the routes the module declares", (group) => {
    const dir = path.join(import.meta.dirname, group);
    const declared = routeTable.routes.filter((r) => r.path.split("/")[1] === group);
    expect(declaredPaths(dir)).toEqual(declared.map((r) => r.path));
  });

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
