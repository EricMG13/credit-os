// The "no browser found" path of open-from-disk.mjs and of the gates wrapper, run for real.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

const scripts = import.meta.dirname;
const emptyPath = mkdtempSync(path.join(tmpdir(), "credit-os-nopath-"));

function run(script, ci) {
  const env = { ...process.env, CHROME_PATH: path.join(emptyPath, "no-browser"), PATH: emptyPath };
  delete env["CI"];
  if (ci) env["CI"] = "true";
  const out = spawnSync(process.execPath, [path.join(scripts, script)], { env, encoding: "utf8" });
  return { status: out.status, text: `${out.stdout}${out.stderr}` };
}

test.after(() => {
  rmSync(emptyPath, { recursive: true, force: true });
});

test("open-from-disk: no browser and CI unset exits 77 with the reason", () => {
  const out = run("open-from-disk.mjs", false);
  assert.equal(out.status, 77);
  assert.match(out.text, /SKIP no supported browser found/);
});

test("open-from-disk: no browser and CI=true exits 1 with the reason", () => {
  const out = run("open-from-disk.mjs", true);
  assert.equal(out.status, 1);
  assert.match(out.text, /FAIL no supported browser found/);
});

test("file-check: 77 is a skip, one clear line, exit 0", () => {
  const out = run("file-check.mjs", false);
  assert.equal(out.status, 0);
  assert.match(out.text, /SKIPPED browser check/);
});

test("file-check: CI=true with no browser is a failure, never a skip", () => {
  const out = run("file-check.mjs", true);
  assert.equal(out.status, 1);
  assert.doesNotMatch(out.text, /SKIPPED/);
});
