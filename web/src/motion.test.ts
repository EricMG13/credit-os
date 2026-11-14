import { readFileSync } from "node:fs";
import path from "node:path";

const css = readFileSync(path.join(import.meta.dirname, "index.css"), "utf8").replace(
  /\r\n/g,
  "\n",
);

describe("index.css", () => {
  it("turns animation and transition off under prefers-reduced-motion", () => {
    const block = /@media \(prefers-reduced-motion: reduce\) \{([^@]*)\}\s*$/.exec(css)?.[1] ?? "";
    const selectors = /^\s*([^{]*?)\s*\{/.exec(block)?.[1]?.split(/\s*,\s*/);
    expect(selectors).toEqual(["*", "::before", "::after"]);
    expect(block).toMatch(/animation:\s*none\s*!important/);
    expect(block).toMatch(/transition:\s*none\s*!important/);
  });
});
