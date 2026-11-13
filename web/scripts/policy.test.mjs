// The content security policy of the built page, pinned exactly so a dropped directive fails the gates.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const POLICY =
  "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'";

test("built dist/index.html carries exactly the pinned content security policy", () => {
  const html = readFileSync(path.join(import.meta.dirname, "..", "dist", "index.html"), "utf8");
  const metas = [...html.matchAll(/<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*>/g)];
  assert.equal(metas.length, 1);
  const content = /\bcontent="([^"]*)"/.exec(metas[0][0])?.[1];
  assert.equal(content, POLICY);
});
