// The asset checks of the open-from-disk script, run on small built-page folders.
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { assetProblems } from "./assets.mjs";

const roots = [];

function page(head, files) {
  const root = mkdtempSync(path.join(tmpdir(), "credit-os-assets-"));
  roots.push(root);
  mkdirSync(path.join(root, "assets"));
  writeFileSync(path.join(root, "index.html"), `<html><head>${head}</head></html>`);
  for (const [name, body] of Object.entries(files)) writeFileSync(path.join(root, name), body);
  return root;
}

const LINK = '<link rel="stylesheet" href="./assets/a.css">';
const SCRIPT = '<script type="module" src="./assets/a.js"></script>';

test.after(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

test("a complete page has no problems", () => {
  const root = page(LINK + SCRIPT, { "assets/a.css": "a{}", "assets/a.js": "1" });
  assert.deepEqual(assetProblems(root), []);
});

test("an empty stylesheet is a problem", () => {
  const root = page(LINK + SCRIPT, { "assets/a.css": "", "assets/a.js": "1" });
  assert.match(assetProblems(root).join("\n"), /empty.*a\.css/);
});

test("a missing stylesheet is a problem", () => {
  const root = page(LINK + SCRIPT, { "assets/a.js": "1" });
  assert.match(assetProblems(root).join("\n"), /missing.*a\.css/);
});

for (const bad of [
  "/assets/a.css",
  "https://example.com/a.css",
  "//example.com/a.css",
  "file:///a.css",
]) {
  test(`stylesheet path ${bad} is a problem`, () => {
    const root = page(`<link rel="stylesheet" href="${bad}">${SCRIPT}`, {
      "assets/a.css": "a{}",
      "assets/a.js": "1",
    });
    assert.match(assetProblems(root).join("\n"), /absolute or has a scheme/);
  });
}

test("a script path starting with / is a problem", () => {
  const root = page(`${LINK}<script type="module" src="/assets/a.js"></script>`, {
    "assets/a.css": "a{}",
    "assets/a.js": "1",
  });
  assert.match(assetProblems(root).join("\n"), /absolute or has a scheme/);
});

test("a page without a stylesheet is a problem", () => {
  const root = page(SCRIPT, { "assets/a.js": "1" });
  assert.match(assetProblems(root).join("\n"), /no stylesheet/);
});
