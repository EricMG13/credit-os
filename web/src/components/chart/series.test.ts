import { readFileSync } from "node:fs";
import path from "node:path";
import { assignSeries, SERIES } from "./series";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");

// The Chart palette table: slot, colour, hex, contrast, gray value, line style.
const start = designSystem.indexOf("| Slot | Colour | Hex |");
const ROWS = designSystem
  .slice(start)
  .split("\n")
  .slice(2)
  .filter((l, i, all) => l.startsWith("|") && all.slice(0, i).every((p) => p.startsWith("|")))
  .map((l) => l.split("|").map((c) => c.trim()));

// Independent of series.ts: what each line-style word means as an SVG stroke-dasharray.
const DASH: Record<string, string> = {
  Solid: "none",
  Dashed: "6 4",
  Dotted: "1.5 4",
  "Dash-dot": "8 4 1.5 4",
};

describe("SERIES", () => {
  it("reads seven rows from the design system", () => {
    expect(ROWS).toHaveLength(7);
    expect(ROWS.at(-1)?.[1]).toBe("Other");
  });

  it("matches the palette table row for row", () => {
    expect(SERIES).toHaveLength(7);
    ROWS.forEach((cells, i) => {
      const slot = (cells[1] ?? "").toLowerCase();
      const [lineWord = "", markerWord = ""] = (cells[6] ?? "").split(", ");
      const entry = SERIES[i];
      expect(entry?.color, `slot ${slot}`).toBe(`var(--color-chart-${slot})`);
      expect(entry?.dash, `slot ${slot} dash`).toBe(DASH[lineWord]);
      const marker = markerWord === "no marker" ? "none" : markerWord.replace(" marker", "");
      expect(entry?.marker, `slot ${slot} marker`).toBe(marker);
    });
  });

  it("names no hex colour", () => {
    expect(JSON.stringify(SERIES)).not.toMatch(/#[0-9A-Fa-f]{3,8}\b/);
  });
});

describe("assignSeries", () => {
  const names = ["a", "b", "c", "d", "e", "f", "g", "h"];

  it("gives the first six names slots 1 to 6 by position", () => {
    const styles = assignSeries(names);
    names.slice(0, 6).forEach((n, i) => {
      expect(styles.get(n)).toEqual(SERIES[i]);
    });
  });

  it("folds the seventh and later names into Other", () => {
    const styles = assignSeries(names);
    expect(styles.get("g")).toEqual(SERIES[6]);
    expect(styles.get("h")).toEqual(SERIES[6]);
    expect(styles.size).toBe(8);
  });
});
