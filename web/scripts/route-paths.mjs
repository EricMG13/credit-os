// The route paths a page group declares, read from its routes.tsx without importing it (a node
// script cannot load TSX). Convention: every route object is written in routes.tsx with a
// literal `path: "/…"` property; src/pages/route-table.test.ts compares them with the real arrays.
import { readFileSync } from "node:fs";
import path from "node:path";

// Whole-line and block comments only: a comment that quotes `path: "/…"` is not a route.
function withoutComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^[ \t]*\/\/.*$/gm, "");
}

export function pathsIn(source) {
  return [...withoutComments(source).matchAll(/\bpath:\s*"(\/[^"]*)"/g)].map((match) => match[1]);
}

/** True when a route object in the source declares `home: "/…"`; the group then has a bare address. */
export function declaresHome(source) {
  return /\bhome:\s*"\//.test(withoutComments(source));
}

export function groupDeclaresHome(groupDir) {
  return declaresHome(readFileSync(path.join(groupDir, "routes.tsx"), "utf8"));
}

export function declaredPaths(groupDir) {
  return pathsIn(readFileSync(path.join(groupDir, "routes.tsx"), "utf8"));
}

/** The hash for a pattern and one parameter set; a segment `:name` is replaced whole, as matchRoute reads it. */
export function fillParams(pattern, set) {
  const missing = [];
  const hash = pattern
    .split("/")
    .map((segment) => {
      if (!segment.startsWith(":")) return segment;
      const name = segment.slice(1);
      if (!Object.hasOwn(set, name)) missing.push(name);
      return encodeURIComponent(set[name] ?? "");
    })
    .join("/");
  return { hash, missing };
}
