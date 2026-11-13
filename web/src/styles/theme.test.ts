import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const here = import.meta.dirname;
const webRoot = path.resolve(here, "..", "..");
const docs = path.resolve(webRoot, "..", "docs", "design");
// A checkout on Windows may carry CRLF line endings; the parsers below expect LF.
const lf = (text: string): string => text.replace(/\r\n/g, "\n");
const designSystem = lf(readFileSync(path.join(docs, "design-system.md"), "utf8"));
const brandTokens = lf(readFileSync(path.join(docs, "brand-tokens.md"), "utf8"));
const themePath = path.join(here, "theme.css");
const theme = existsSync(themePath) ? lf(readFileSync(themePath, "utf8")) : "";

const HEX = /#[0-9A-Fa-f]{6}\b/g;

function sectionOf(text: string, title: string, level: "##" | "###"): string {
  const start = text.indexOf(`\n${level} ${title}\n`);
  if (start < 0) throw new Error(`no section ${title}`);
  const rest = text.slice(start + 1);
  const next = rest.slice(level.length + 1).search(/\n##+ /);
  return next < 0 ? rest : rest.slice(0, next + level.length + 1);
}

function section(title: string, level: "##" | "###"): string {
  return sectionOf(designSystem, title, level);
}

function declared(name: string): string | undefined {
  const m = new RegExp(`--${name}:\\s*([^;]+);`).exec(theme);
  return m?.[1]?.trim();
}

function need(value: string | undefined, what: string): string {
  if (value === undefined) throw new Error(`missing ${what}`);
  return value;
}

function plain(css: string | undefined): string {
  return need(css, "value")
    .replace(/\s/g, "")
    .replace(/(?<!\d)0\./g, ".");
}

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );
}

describe("theme.css", () => {
  it("reads sections the same from text with CRLF line endings", () => {
    const crlf = designSystem.replace(/\n/g, "\r\n");
    for (const [title, level] of [
      ["Surface", "###"],
      ["Status", "###"],
      ["Gap states", "###"],
      ["Space, radius, elevation, borders", "##"],
    ] as const) {
      expect(sectionOf(lf(crlf), title, level), title).toBe(section(title, level));
    }
  });

  it("exists", () => {
    expect(existsSync(themePath), "theme.css not found").toBe(true);
  });

  it("defines every colour-role token with the design system's hex", () => {
    const pairs: [string, string][] = [];
    for (const title of ["Surface", "Text", "Action, hover and focus", "Border"]) {
      for (const m of section(title, "###").matchAll(
        /\|\s*`([a-z-]+)`\s*\|\s*`(#[0-9A-Fa-f]{6})`/g,
      )) {
        pairs.push([need(m[1], "token"), need(m[2], "hex")]);
      }
    }
    expect(pairs.length).toBeGreaterThan(20);
    for (const [name, hex] of pairs) {
      expect(declared(`color-${name}`)?.toUpperCase(), name).toBe(hex.toUpperCase());
    }
  });

  it("defines the four status tokens per status, parsed by column", () => {
    const rows = section("Status", "###")
      .split("\n")
      .filter((l) => /^\|\s*(Success|Warning|Error|Info)\s*\|/.test(l));
    expect(rows).toHaveLength(4);
    for (const row of rows) {
      const cells = row.split("|").map((c) => c.trim());
      const status = need(cells[1], "status").toLowerCase();
      ["text", "fill", "edge", "mark"].forEach((part, i) => {
        const hex = need(/#[0-9A-Fa-f]{6}/.exec(cells[3 + i] ?? "")?.[0], `${status} ${part}`);
        expect(declared(`color-${status}-${part}`)?.toUpperCase(), `${status}-${part}`).toBe(
          hex.toUpperCase(),
        );
      });
    }
  });

  it("defines the gap text colour from the Gap states table", () => {
    const hex = need(
      /violet text `(#[0-9A-Fa-f]{6})`/.exec(section("Gap states", "###"))?.[1],
      "gap text hex",
    );
    expect(declared("color-gap-text")?.toUpperCase()).toBe(hex.toUpperCase());
  });

  it("defines the radius, shadow and type tokens from the design system", () => {
    const space = section("Space, radius, elevation, borders", "##");
    for (const m of space.matchAll(/\|\s*`radius-(xs|sm|md|lg|full)`\s*\|\s*([0-9]+px)/g)) {
      const size = need(m[1], "radius");
      expect(declared(`radius-ds-${size}`), size).toBe(m[2]);
    }
    for (const m of space.matchAll(/\|\s*`shadow-([12])`\s*\|\s*`([^`]+)`/g)) {
      const n = need(m[1], "shadow");
      expect(plain(declared(`shadow-${n}`)), `shadow-${n}`).toBe(plain(m[2]));
    }
    const type = section("Type", "##");
    const rows = [
      ...type.matchAll(
        /\|\s*`(\w+)`\s*\|\s*(\d+) \/ (\d+)\s*\|\s*(\d+)\s*\|[^|]*\|\s*(-?[\d.]+)(em)?\s*\|/g,
      ),
    ];
    expect(rows).toHaveLength(11);
    for (const row of rows) {
      const name = need(row[1], "name");
      const size = need(row[2], "size");
      const line = need(row[3], "line");
      const weight = need(row[4], "weight");
      const track = need(row[5], "tracking");
      expect(declared(`text-${name}`), name).toBe(`${size}px`);
      expect(declared(`text-${name}--line-height`), name).toBe(`${line}px`);
      expect(declared(`text-${name}--font-weight`), name).toBe(weight);
      expect(Number.parseFloat(declared(`text-${name}--letter-spacing`) ?? "x"), name).toBe(
        Number.parseFloat(track),
      );
    }
  });

  it("names the three font families from the Type table", () => {
    expect(declared("font-display")).toContain('"Schibsted Grotesk"');
    expect(declared("font-body")).toContain('"Geist"');
    expect(declared("font-mono")).toContain('"Geist Mono"');
  });

  it("uses only hexes that appear in brand-tokens.md", () => {
    const allowed = new Set((brandTokens.match(HEX) ?? []).map((h) => h.toUpperCase()));
    const used = (theme.match(HEX) ?? []).map((h) => h.toUpperCase());
    expect(used.length).toBeGreaterThan(0);
    expect(used.filter((h) => !allowed.has(h))).toEqual([]);
  });

  it("names a file that exists for every @font-face url", () => {
    const urls = [...theme.matchAll(/@font-face\s*{[^}]*?url\(\s*["']?([^"')]+)["']?\s*\)/g)].map(
      (m) => need(m[1], "url"),
    );
    expect(urls).toHaveLength(7);
    for (const url of urls) {
      expect(existsSync(path.join(webRoot, "public", url.replace(/^\.?\//, ""))), url).toBe(true);
    }
  });

  it("is the only file under web/src with a hex colour", () => {
    const offenders = walk(path.resolve(webRoot, "src"))
      .filter((f) => path.relative(here, f) !== "theme.css")
      .filter((f) => /#[0-9A-Fa-f]{6}\b/.test(readFileSync(f, "utf8")))
      .map((f) => path.relative(webRoot, f));
    expect(offenders).toEqual([]);
  });
});
