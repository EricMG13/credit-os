// Opens every route the page groups declare, from file:// with the fixture data, using the browser
// helpers open-from-disk.mjs passes in.
import { cpSync } from "node:fs";
import path from "node:path";
import { declaredPaths, fillParams, groupDeclaresHome } from "./route-paths.mjs";
import { GROUPS, readFixture, writeDataFile } from "./fixture-data.mjs";

const pagesDir = path.resolve(import.meta.dirname, "..", "src", "pages");
const NOT_FOUND = "Page not found";
const NOT_BUILT = "Not built yet";
const UNREADABLE = "This part of the library could not be read";

function visitsFor(group) {
  const params = readFixture(group).params ?? {};
  const visits = [];
  const failures = [];
  for (const pattern of declaredPaths(path.join(pagesDir, group))) {
    const sets = pattern.includes(":") ? (params[pattern] ?? []) : [{}];
    if (sets.length === 0)
      failures.push(`${pattern} is parameterised and fixtures/${group}.json has no params for it`);
    for (const set of sets) {
      const { hash, missing } = fillParams(pattern, set);
      for (const name of missing)
        failures.push(`${pattern}: a parameter set in fixtures/${group}.json lacks "${name}"`);
      visits.push({
        label: hash === pattern ? pattern : `${pattern} as ${hash}`,
        hash: `#${hash}`,
      });
    }
  }
  // A group that declares a home also owns its bare address, which must draw that page.
  if (groupDeclaresHome(path.join(pagesDir, group))) {
    const bare = group === "library" ? "/" : `/${group}`;
    visits.push({ label: `bare address ${bare}`, hash: `#${bare}` });
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
    for (const failure of failures) console.log(`FAIL route ${group}: ${failure}`);
    results.push(...failures.map(() => false));
  }
  const visits = all.flatMap(({ group, visits }) => visits.map((visit) => ({ group, ...visit })));
  if (visits.length === 0 && results.length === 0) {
    console.log("PASS route visits: zero routes were declared by the page groups");
    results.push(true);
  }
  for (const { group, label, hash } of visits) {
    const { dom, log } = dumpPage(browser, copy, hash);
    const found = problems(log);
    const present = ["<style", NOT_FOUND, NOT_BUILT, UNREADABLE].filter((text) =>
      dom.includes(text),
    );
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
  return [...results, unknownOk].every(Boolean);
}
