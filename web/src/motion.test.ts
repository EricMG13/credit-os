import { readFileSync } from "node:fs";
import path from "node:path";

const css = readFileSync(path.join(import.meta.dirname, "index.css"), "utf8").replace(
  /\r\n/g,
  "\n",
);

describe("index.css", () => {
  it("turns animation and transition off under prefers-reduced-motion", () => {
    const block = /@media \(prefers-reduced-motion: reduce\) \{([^@]*)\}\s*$/.exec(css)?.[1] ?? "";
    expect(block).toMatch(/animation:\s*none\s*!important/);
    expect(block).toMatch(/transition:\s*none\s*!important/);
  });
});
