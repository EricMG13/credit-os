// The route paths a page group declares, read from its routes.tsx without importing it (a node
// script cannot load TSX). Convention: every route object is written in routes.tsx with a
// literal `path: "/…"` property. src/pages/route-table.test.ts compares these paths with the real
// route arrays, so a route written another way fails the gates.
import { readFileSync } from "node:fs";
import path from "node:path";

// Whole-line and block comments only: a comment that quotes `path: "/…"` is not a route.
function withoutComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^[ \t]*\/\/.*$/gm, "");
}

export function pathsIn(source) {
  return [...withoutComments(source).matchAll(/\bpath:\s*"(\/[^"]*)"/g)].map((match) => match[1]);
}

export function declaredPaths(groupDir) {
  return pathsIn(readFileSync(path.join(groupDir, "routes.tsx"), "utf8"));
}
