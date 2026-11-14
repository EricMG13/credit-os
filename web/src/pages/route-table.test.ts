import path from "node:path";
import { declaredPaths, pathsIn } from "../../scripts/route-paths.mjs";
import { SLICE_KEYS } from "../data";
import { matchRoute, routeTable, type Route } from "./route-table";

function route(pathPattern: string): Route {
  return { path: pathPattern, title: pathPattern, render: () => null as never };
}

describe("matchRoute", () => {
  const routes = [route("/library/:issuer/:run/overview"), route("/model/about"), route("/x")];

  it("captures the named segments of a parameterised path", () => {
    const found = matchRoute("/library/tdg/r1/overview", routes);
    expect(found?.route.path).toBe("/library/:issuer/:run/overview");
    expect(found?.params).toEqual({ issuer: "tdg", run: "r1" });
  });

  it("returns null for an unknown path", () => {
    expect(matchRoute("/library/tdg/r1/changes", routes)).toBeNull();
    expect(matchRoute("/nowhere", routes)).toBeNull();
    expect(matchRoute("", routes)).toBeNull();
  });

  it("ignores one trailing slash", () => {
    expect(matchRoute("/model/about/", routes)?.route.path).toBe("/model/about");
    expect(matchRoute("/library/tdg/r1/overview/", routes)?.params).toEqual({
      issuer: "tdg",
      run: "r1",
    });
  });

  it("does not ignore a second trailing slash", () => {
    expect(matchRoute("/model/about//", routes)).toBeNull();
  });

  it("decodes a captured segment", () => {
    expect(matchRoute("/library/a%20b/r%2F1/overview", routes)?.params).toEqual({
      issuer: "a b",
      run: "r/1",
    });
  });

  it("rejects an empty segment for a parameter", () => {
    expect(matchRoute("/library//r1/overview", routes)).toBeNull();
  });

  it("rejects a malformed escape instead of throwing", () => {
    expect(matchRoute("/library/%E0%A4%A/r1/overview", routes)).toBeNull();
  });

  it("lets the first matching route win", () => {
    const first = route("/a/:one");
    const second = route("/a/:two");
    expect(matchRoute("/a/v", [first, second])?.route).toBe(first);
  });

  it("does not treat a name from Object.prototype as a parameter value store", () => {
    const found = matchRoute("/a/constructor", [route("/a/:toString")]);
    expect(found?.params).toEqual({ toString: "constructor" });
    expect(Object.getPrototypeOf(found?.params)).toBeNull();
  });

  it("does not match a query string or a longer path", () => {
    expect(matchRoute("/x?a=1", routes)).toBeNull();
    expect(matchRoute("/x/y", routes)).toBeNull();
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

describe("the real page groups", () => {
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
