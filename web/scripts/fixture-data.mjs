// Writes the data file the library opens from disk, from the four page-group fixtures.
// Usage: node scripts/fixture-data.mjs <outDir> [fixturesDir]
// A fixture is { "slice"?: <the group's slice>, "params"?: { "<route path>": [ { "<name>": "<value>" } ] } },
// and library.json may also carry "issuers": [ { "id", "name" } ].
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const GROUPS = ["library", "model", "run", "signal"];
const defaultDir = path.resolve(import.meta.dirname, "..", "fixtures");

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function paramProblem(params) {
  if (!isObject(params)) return '"params" must be an object';
  for (const [pattern, sets] of Object.entries(params)) {
    if (!Array.isArray(sets) || !sets.every(isObject)) {
      return `"params" for "${pattern}" must be a list of objects`;
    }
    for (const set of sets) {
      if (!Object.values(set).every((value) => typeof value === "string")) {
        return `"params" for "${pattern}" must hold string values`;
      }
    }
  }
  return undefined;
}

/** The parsed fixture of one group. Throws an error naming the file when it is not valid. */
export function readFixture(group, dir = defaultDir) {
  const file = `${group}.json`;
  let value;
  try {
    value = JSON.parse(readFileSync(path.join(dir, file), "utf8"));
  } catch (error) {
    throw new Error(`${file}: ${error.message}`, { cause: error });
  }
  if (!isObject(value)) throw new Error(`${file}: must be a JSON object`);
  const known = group === "library" ? ["slice", "params", "issuers"] : ["slice", "params"];
  for (const key of Object.keys(value)) {
    if (!known.includes(key)) throw new Error(`${file}: unknown key "${key}"`);
  }
  const problem = "params" in value ? paramProblem(value.params) : undefined;
  if (problem) throw new Error(`${file}: ${problem}`);
  if ("issuers" in value && !Array.isArray(value.issuers)) {
    throw new Error(`${file}: "issuers" must be a list`);
  }
  return value;
}

/** The object window.CREDIT_OS_DATA holds: a group's member is omitted when its fixture has no slice. */
export function buildData(dir = defaultDir) {
  const fixtures = Object.fromEntries(GROUPS.map((group) => [group, readFixture(group, dir)]));
  const data = { schema: "credit-os-data/1", issuers: fixtures.library.issuers ?? [] };
  for (const group of GROUPS) {
    if ("slice" in fixtures[group]) data[group] = fixtures[group].slice;
  }
  return data;
}

export function writeDataFile(outDir, dir = defaultDir) {
  const text = `window.CREDIT_OS_DATA = ${JSON.stringify(buildData(dir), null, 2)};\n`;
  mkdirSync(outDir, { recursive: true });
  writeFileSync(path.join(outDir, "data.js"), text);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [outDir, dir] = process.argv.slice(2);
  if (!outDir) {
    console.error("usage: node scripts/fixture-data.mjs <outDir> [fixturesDir]");
    process.exit(2);
  }
  try {
    writeDataFile(path.resolve(outDir), dir ? path.resolve(dir) : defaultDir);
  } catch (error) {
    console.error(`fixture data: ${error.message}`);
    process.exit(1);
  }
}
