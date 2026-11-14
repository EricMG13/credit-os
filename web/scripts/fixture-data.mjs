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

function badParams(params) {
  if (!isObject(params)) return '"params" must be an object';
  const bad = Object.entries(params).find(
    ([, sets]) =>
      !Array.isArray(sets) ||
      !sets.every((set) => isObject(set) && Object.values(set).every((v) => typeof v === "string")),
  );
  return bad && `"params" for "${bad[0]}" must be a list of objects with string values`;
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
  const problem =
    ("params" in value && badParams(value.params)) ||
    ("issuers" in value && !Array.isArray(value.issuers) && '"issuers" must be a list');
  if (problem) throw new Error(`${file}: ${problem}`);
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
  // JSON.parse of a string keeps a "__proto__" key an own key (an object literal would not); `<`
  // and the line separators are escaped so the text is safe inside a script element.
  const literal = JSON.stringify(JSON.stringify(buildData(dir))).replace(
    /[<\u2028\u2029]/g,
    (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
  mkdirSync(outDir, { recursive: true });
  writeFileSync(path.join(outDir, "data.js"), `window.CREDIT_OS_DATA = JSON.parse(${literal});\n`);
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
