import { readFileSync } from "node:fs";
import path from "node:path";
import { STATUS_SETS } from "./sets";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");

interface Row {
  word: string;
  shape: string;
  tone: string;
}

// The "Set | State, shape and colour family" table, parsed from the design system.
function parseSets(): Map<string, Row[]> {
  const start = designSystem.indexOf("| Set | State, shape and colour family |");
  if (start < 0) throw new Error("no set table");
  const sets = new Map<string, Row[]>();
  for (const line of designSystem.slice(start).split("\n").slice(2)) {
    if (!line.startsWith("|")) break;
    const [, name = "", cell = ""] = line.split("|").map((c) => c.trim());
    const rows = cell
      .split(/\.(?:\s+|$)/)
      .filter((s) => s.length > 0)
      .map((s) => {
        const [head = "", rest = ""] = s.split(/:\s+/);
        const [shape = "", tone] = rest.split(/,\s+/);
        const word = head.replace(/\s*\(.*\)$/, "");
        const family = tone === undefined ? word.toLowerCase() : tone.replace(/ colours$/, "");
        return { word, shape, tone: family };
      });
    sets.set(name, rows);
  }
  return sets;
}

const parsed = parseSets();
const COUNTS: [string, number][] = [
  ["Status", 4],
  ["Run states", 7],
  ["Signal source states", 6],
  ["Dated records", 3],
  ["Answer state", 3],
  ["Met or not met", 2],
  ["Freshness", 2],
  ["Module state", 4],
  ["Change state", 3],
  ["Gap severity", 3],
  ["File state", 4],
  ["Approval", 1],
  ["Activity that cannot be read", 1],
];

describe("STATUS_SETS", () => {
  it("parses 13 sets with the stated number of states each", () => {
    expect(parsed.size).toBe(13);
    for (const [name, count] of COUNTS) {
      expect(parsed.get(name)?.length, name).toBe(count);
    }
  });

  it("matches the design system row for row", () => {
    expect(Object.keys(STATUS_SETS)).toEqual([...parsed.keys()]);
    for (const [name, rows] of parsed) {
      const set = STATUS_SETS[name as keyof typeof STATUS_SETS] as Record<
        string,
        { shape: string; tone: string; word: string }
      >;
      expect(
        Object.values(set).map((s) => s.word),
        name,
      ).toEqual(rows.map((r) => r.word));
      for (const row of rows) {
        expect(set[row.word], `${name}: ${row.word}`).toEqual({
          shape: row.shape,
          tone: row.tone,
          word: row.word,
        });
      }
    }
  });

  it("gives no two states of one set the same shape", () => {
    for (const [name, set] of Object.entries(STATUS_SETS)) {
      const shapes = Object.values(set).map((s) => s.shape);
      expect(new Set(shapes).size, name).toBe(shapes.length);
    }
  });

  it("shares only the slashed circle between module state and change state", () => {
    const module = new Set(Object.values(STATUS_SETS["Module state"]).map((s) => s.shape));
    const change = Object.values(STATUS_SETS["Change state"]).map((s) => s.shape);
    expect(change.filter((s) => module.has(s))).toEqual(["slashed circle"]);
  });
});
