// The static asset checks of the built index.html, shared by open-from-disk.mjs and its tests.
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

// Every stylesheet and script the built index.html references, as paths inside the folder.
// A file missing from the folder is not logged by Chrome from file://, so it is checked here.
export function referencedAssets(folder) {
  const html = readFileSync(path.join(folder, "index.html"), "utf8");
  const sheets = [...html.matchAll(/<link\b[^>]*\brel="stylesheet"[^>]*>/g)].map((m) => ({
    kind: "stylesheet",
    ref: /\bhref="([^"]*)"/.exec(m[0])?.[1],
  }));
  const scripts = [...html.matchAll(/<script\b[^>]*>/g)].map((m) => ({
    kind: "script",
    ref: /\bsrc="([^"]*)"/.exec(m[0])?.[1],
  }));
  return { assets: [...sheets, ...scripts], hasStyle: sheets.length > 0 };
}

// A browser does not load a path that starts with "/" or carries a scheme from disk.
const NOT_RELATIVE = /^(?:\/|[a-zA-Z][a-zA-Z0-9+.-]*:)/;

// Returns one message per problem; an empty list means the references are sound.
export function assetProblems(folder) {
  const { assets, hasStyle } = referencedAssets(folder);
  const problems = [];
  if (!hasStyle) problems.push("index.html has no stylesheet link");
  if (assets.length === 0) problems.push("index.html references no assets");
  for (const { kind, ref } of assets) {
    if (ref === undefined) {
      problems.push(`${kind} reference has no path`);
    } else if (NOT_RELATIVE.test(ref)) {
      problems.push(`${kind} path is absolute or has a scheme: ${ref}`);
    } else {
      const file = path.join(folder, ...ref.split("/"));
      if (!existsSync(file)) problems.push(`missing or unreadable ${kind}: ${ref}`);
      else if (kind === "stylesheet" && statSync(file).size === 0) {
        problems.push(`empty stylesheet: ${ref}`);
      }
    }
  }
  return problems;
}
