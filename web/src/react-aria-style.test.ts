import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

// React Aria injects a <style> element for pressables unless one with this id already exists.
// The content security policy forbids the injection, so index.html carries the id and the
// project stylesheet carries the rule. These tests fail if a library upgrade changes the guard.
const lf = (text: string): string => text.replace(/\r\n/g, "\n");
const webRoot = path.resolve(import.meta.dirname, "..");
const requireFrom = createRequire(path.join(webRoot, "package.json"));
const usePress = lf(
  readFileSync(
    path.join(
      path.dirname(requireFrom.resolve("react-aria/package.json")),
      "dist",
      "private",
      "interactions",
      "usePress.mjs",
    ),
    "utf8",
  ),
);

describe("the React Aria pressable style", () => {
  it("is still injected under this id, guarded by a lookup of the id, with this rule", () => {
    expect(usePress).toContain("'react-aria-pressable-style'");
    expect(usePress).toMatch(/ownerDocument\.getElementById\([^)]*STYLE_ID\)\)\s*return;/);
    expect(usePress).toContain("'data-react-aria-pressable'");
    expect(usePress).toMatch(
      /\[\$\{[^}]*PRESSABLE_ATTRIBUTE\}\]\s*\{\s*touch-action: pan-x pan-y pinch-zoom;/,
    );
  });

  it("is claimed by an element in index.html that is not a style element", () => {
    const html = lf(readFileSync(path.join(webRoot, "index.html"), "utf8"));
    expect(html).toMatch(/<meta\s+id="react-aria-pressable-style"\s*\/?>/);
    expect(html).not.toMatch(/<style/);
  });

  it("has its rule in the project stylesheet", () => {
    const css = lf(readFileSync(path.join(webRoot, "src", "index.css"), "utf8"));
    expect(css).toMatch(
      /\[data-react-aria-pressable\]\s*\{\s*touch-action: pan-x pan-y pinch-zoom;\s*\}/,
    );
  });
});
