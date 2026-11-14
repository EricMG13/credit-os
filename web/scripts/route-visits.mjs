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

/** The visits for one group; `pages` and `fixtures` default to the real folders, a test passes stubs. */
export function visitsFor(group, pages = pagesDir, fixtures = undefined) {
  const params = readFixture(group, fixtures).params ?? {};
  const visits = [];
  const failures = [];
  for (const pattern of declaredPaths(path.join(pages, group))) {
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
  if (groupDeclaresHome(path.join(pages, group))) {
    const bare = group === "library" ? "/" : `/${group}`;
    visits.push({ label: `bare address ${bare}`, hash: `#${bare}`, bare: true });
  }
  return { visits, failures };
}

/**
 * What is wrong with the live DOM of one visit: an injected style, a failure text, and not exactly
 * one h1 (the page title; a full-bleed page draws its own). "Not built yet" is only a failure at a
 * bare address, where a declared home must have replaced it; a real page may contain those words.
 */
export function domProblems(dom, bare) {
  const texts = ["<style", NOT_FOUND, UNREADABLE, ...(bare ? [NOT_BUILT] : [])];
  const problems = texts
    .filter((text) => dom.includes(text))
    .map((text) => `the live DOM contains "${text}"`);
  const h1 = (dom.match(/<h1[\s>]/g) ?? []).length;
  if (h1 !== 1) problems.push(`the live DOM has ${h1} h1 elements, expected exactly 1`);
  return problems;
}

/** True when the library group declares a home: the default address then draws a page of its own. */
export function libraryDeclaresHome(pages = pagesDir) {
  return groupDeclaresHome(path.join(pages, "library"));
}

/**
 * What is wrong with the DOM at the default address when the library declares a home: that page
 * must be one real page (one main, one h1) and none of the placeholder or failure texts.
 */
export function defaultAddressProblems(dom) {
  const problems = domProblems(dom, true);
  for (const text of ["Library data is missing", "This library was written by a newer version"])
    if (dom.includes(text)) problems.push(`the live DOM contains "${text}"`);
  const mains = (dom.match(/<main[\s>]/g) ?? []).length;
  if (mains !== 1) problems.push(`the live DOM has ${mains} main elements, expected exactly 1`);
  return problems;
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
  for (const { group, label, hash, bare } of visits) {
    const { dom, log } = dumpPage(browser, copy, hash);
    const found = problems(log);
    const present = domProblems(dom, bare === true);
    const rendered = dom.includes("<main");
    const ok = found.length === 0 && present.length === 0 && rendered;
    console.log(`${ok ? "PASS" : "FAIL"} route ${group} ${label}`);
    if (!ok) {
      if (!rendered) console.log("  the page rendered no <main> region");
      for (const needle of found) console.log(`  stderr contains "${needle}"`);
      for (const problem of present) console.log(`  ${problem}`);
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
