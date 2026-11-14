// Opens every route the page groups declare in the built library, from file://, with the fixture
// data. open-from-disk.mjs passes in its own browser helpers so this module stays self-contained.
import { cpSync } from "node:fs";
import path from "node:path";
import { declaredPaths } from "./route-paths.mjs";
import { GROUPS, readFixture, writeDataFile } from "./fixture-data.mjs";

const pagesDir = path.resolve(import.meta.dirname, "..", "src", "pages");
const NOT_FOUND = "Page not found";
const UNREADABLE = "This part of the library could not be read";

function visitsFor(group) {
  const params = readFixture(group).params ?? {};
  const visits = [];
  const failures = [];
  for (const pattern of declaredPaths(path.join(pagesDir, group))) {
    if (!pattern.includes(":")) {
      visits.push({ label: pattern, hash: `#${pattern}` });
      continue;
    }
    const sets = params[pattern] ?? [];
    if (sets.length === 0)
      failures.push(`${pattern} is parameterised and fixtures/${group}.json has no params for it`);
    for (const set of sets) {
      const hash = pattern.replace(/:(\w+)/g, (_, name) => {
        if (!(name in set))
          failures.push(`${pattern}: a parameter set in fixtures/${group}.json lacks "${name}"`);
        return encodeURIComponent(set[name] ?? "");
      });
      visits.push({ label: `${pattern} as ${hash}`, hash: `#${hash}` });
    }
  }
  return { visits, failures };
}

/** Prints one PASS or FAIL line per visit and returns true when every one passed. */
export function checkRoutes({ browser, folder, work, dumpPage, problems }) {
  const copy = path.join(work, "routes");
  cpSync(folder, copy, { recursive: true });
  writeDataFile(copy);
  const all = GROUPS.map((group) => ({ group, ...visitsFor(group) }));
  const results = [];
  for (const { group, failures } of all) {
    for (const failure of failures) {
      console.log(`FAIL route ${group}: ${failure}`);
      results.push(false);
    }
  }
  const visits = all.flatMap(({ group, visits }) => visits.map((visit) => ({ group, ...visit })));
  if (visits.length === 0 && results.length === 0) {
    console.log("PASS route visits: zero routes were declared by the page groups");
    results.push(true);
  }
  for (const { group, label, hash } of visits) {
    const { dom, log } = dumpPage(browser, copy, hash);
    const found = problems(log);
    const present = ["<style", NOT_FOUND, UNREADABLE].filter((text) => dom.includes(text));
    const rendered = dom.includes("<main");
    const ok = found.length === 0 && present.length === 0 && rendered;
    console.log(`${ok ? "PASS" : "FAIL"} route ${group} ${label}`);
    if (!ok) {
      if (!rendered) console.log("  the page rendered no <main> region");
      for (const needle of found) console.log(`  stderr contains "${needle}"`);
      for (const text of present) console.log(`  the live DOM contains "${text}"`);
      console.log(`  stderr:\n${log}\n  dom:\n${dom}`);
    }
    results.push(ok);
  }
  const unknown = dumpPage(browser, copy, "#/no-such-page");
  const unknownOk = unknown.dom.includes(NOT_FOUND) && problems(unknown.log).length === 0;
  console.log(
    `${unknownOk ? "PASS" : "FAIL"} route visits: an unknown hash expects "${NOT_FOUND}"`,
  );
  if (!unknownOk) console.log(`  stderr:\n${unknown.log}\n  dom:\n${unknown.dom}`);
  results.push(unknownOk);
  return results.every(Boolean);
}
