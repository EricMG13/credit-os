import type { ReactElement } from "react";
import type { SliceKey } from "../data";
import { readSlice as readLibrary, routes as libraryRoutes } from "./library/routes";
import { readSlice as readModel, routes as modelRoutes } from "./model/routes";
import { readSlice as readRun, routes as runRoutes } from "./run/routes";
import { readSlice as readSignal, routes as signalRoutes } from "./signal/routes";

/**
 * `path` is a pattern with `:name` segments, for example `/library/:issuer/:run/overview`.
 * `home` is a concrete address that `path` matches; the group's bare address (`#/signal`, or `#/`
 * for the library) draws the group's first route with a home as if it were that address, for
 * example path `/signal/:space/feed/:tab` with home `/signal/main/feed/for-you`.
 * `layout: "bleed"` draws the page edge to edge with no App header and no padding on `main`;
 * the page then draws its own header. Absent means the padded layout with the title as the h1.
 */
export type Route = {
  path: string;
  home?: string;
  layout?: "bleed";
  title: string;
  render: (params: Record<string, string>) => ReactElement;
};

export type SliceResult<T> =
  { kind: "ok"; data: T } | { kind: "absent" } | { kind: "invalid"; reason: string };

type SliceReader = (source: unknown) => SliceResult<unknown>;

/** Every route, and each group's reader for its member of the data file. */
export type RouteTable = {
  routes: readonly Route[];
  readers: Readonly<Record<SliceKey, SliceReader>>;
};

function matchSegments(
  pattern: readonly string[],
  actual: readonly string[],
): Record<string, string> | null {
  if (pattern.length !== actual.length) return null;
  const params: Record<string, string> = Object.create(null) as Record<string, string>;
  for (const [index, want] of pattern.entries()) {
    const got = actual[index];
    if (got === undefined) return null;
    if (want.startsWith(":")) {
      if (got === "") return null;
      try {
        params[want.slice(1)] = decodeURIComponent(got);
      } catch {
        // A malformed escape is an address no route can own, so it matches nothing.
        return null;
      }
    } else if (want !== got) {
      return null;
    }
  }
  return params;
}

/**
 * `hash` is what useHashRoute returns. `:name` captures one non-empty segment (decoded), one
 * trailing slash is ignored and the first matching route wins. No wildcard, optional segment or query.
 */
export function matchRoute(
  hash: string,
  routes: readonly Route[],
): { route: Route; params: Record<string, string> } | null {
  const actual = (hash.endsWith("/") ? hash.slice(0, -1) : hash).split("/");
  for (const route of routes) {
    const params = matchSegments(route.path.split("/"), actual);
    if (params !== null) return { route, params };
  }
  return null;
}

/** One message per route whose `home` has a `:` segment, is not matched to that route, or leaves its group. */
export function homeProblems(routes: readonly Route[]): string[] {
  const problems: string[] = [];
  for (const route of routes) {
    const home = route.home;
    if (home === undefined) continue;
    const group = route.path.split("/")[1] ?? "";
    if (home.split("/").some((segment) => segment.startsWith(":")))
      problems.push(`${route.path}: home ${home} has a : segment`);
    else if (!home.startsWith(`/${group}/`))
      problems.push(`${route.path}: home ${home} is outside /${group}/`);
    else if (matchRoute(home, routes)?.route !== route)
      problems.push(`${route.path}: home ${home} is not matched to this route`);
  }
  return problems;
}

export const routeTable: RouteTable = {
  routes: [...libraryRoutes, ...modelRoutes, ...runRoutes, ...signalRoutes],
  readers: { library: readLibrary, model: readModel, run: readRun, signal: readSignal },
};
